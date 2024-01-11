from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Request
from PPpackage_utils.http_stream import HTTPRequestReader
from PPpackage_utils.server import Server, StreamingResponse
from PPpackage_utils.stream import Reader, dump_bytes_chunked, dump_many_async
from PPpackage_utils.tar import archive as tar_archive
from PPpackage_utils.tar import extract as tar_extract
from PPpackage_utils.utils import TemporaryDirectory
from pydantic import AnyUrl
from pydantic_settings import BaseSettings
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY

from .database import Installation, User, get_installation
from .framework import framework
from .interface import Interface
from .schemes import Dependency, Options, Package, PackageIDAndInfo, Product
from .user import create_user_kwargs

RequirementType = TypeVar("RequirementType")

SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")


@asynccontextmanager
async def load_tar_and_extract(reader: Reader, present: bool):
    if not present:
        yield None
        return

    tar_bytes = await reader.load_bytes_chunked()

    with TemporaryDirectory() as destination_path:
        tar_extract(tar_bytes, destination_path)

        yield destination_path


class SubmanagerServer(Server, Generic[SettingsType, StateType, RequirementType]):
    def __init__(
        self,
        Settings: type[SettingsType],
        interface: Interface[SettingsType, StateType, RequirementType],
        Requirement: type[RequirementType],
    ):
        class ServerSettings(Settings):
            database_url: AnyUrl = AnyUrl("")
            installations_path: Path = Path("/tmp")

        settings = ServerSettings()

        super().__init__(
            settings,
            framework,
            settings.database_url,
            interface.lifespan,
            User,
            create_user_kwargs,
        )

        async def resolve(
            request: Request,
            state: Annotated[StateType, Depends(framework.get_state)],
        ):
            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)

            requirements_list = (
                reader.load_many(Requirement) async for _ in reader.load_loop()
            )

            output = interface.resolve(
                settings,  # type: ignore
                state,
                options,
                requirements_list,
            )

            return StreamingResponse(HTTP_200_OK, partial(dump_many_async, output))

        async def fetch(
            request: Request,
            state: Annotated[StateType, Depends(framework.get_state)],
            package_name: str,
            package_version: str,
            installation_present: bool,
            generators_present: bool,
        ):
            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)

            async with (
                load_tar_and_extract(reader, installation_present) as installation_path,
                load_tar_and_extract(reader, generators_present) as generators_path,
            ):
                dependencies = reader.load_many(Dependency)

                output = await interface.fetch(
                    settings,  # type: ignore
                    state,
                    options,
                    Package(package_name, package_version),
                    dependencies,
                    installation_path,
                    generators_path,
                )

            if not isinstance(output, PackageIDAndInfo):
                return StreamingResponse(
                    HTTP_422_UNPROCESSABLE_ENTITY, partial(dump_many_async, output)
                )

            return output

        async def generate(
            request: Request,
            state: Annotated[StateType, Depends(framework.get_state)],
        ):
            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)
            products = reader.load_many(Product)
            generators = reader.load_many(str)

            generators = await interface.generate(
                settings,  # type: ignore
                state,
                options,
                products,
                generators,
            )

            return StreamingResponse(
                HTTP_200_OK, partial(dump_bytes_chunked, generators)
            )

        async def install_patch(
            state: Annotated[StateType, Depends(framework.get_state)],
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            user: Annotated[User, Depends(framework.get_user)],
            id: str,
            package_name: str,
            package_version: str,
            product_id: str,
        ):
            installation_db = await get_installation(session, id, user.id)

            await interface.install(
                settings,  # type: ignore
                state,
                installation_db.path,
                Product(package_name, package_version, product_id),
            )

        async def install_post(
            request: Request,
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            user: Annotated[User, Depends(framework.get_user)],
        ):
            reader = HTTPRequestReader(request)

            installation = await reader.load_bytes_chunked()

            installation_path = Path(mkdtemp(dir=settings.installations_path))

            tar_extract(installation, installation_path)

            installation_db = Installation(path=installation_path)
            installation_db.user = user
            session.add(installation_db)
            await session.commit()
            await session.refresh(installation_db)

            return installation_db.id

        async def install_put(
            request: Request,
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            user: Annotated[User, Depends(framework.get_user)],
            id: str,
        ):
            reader = HTTPRequestReader(request)

            installation = await reader.load_bytes_chunked()

            installation_db = await get_installation(session, id, user.id)

            tar_extract(installation, installation_db.path)

        async def install_get(
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            user: Annotated[User, Depends(framework.get_user)],
            id: str,
        ):
            installation_db = await get_installation(session, id, user.id)

            installation = tar_archive(installation_db.path)

            return StreamingResponse(
                HTTP_200_OK, partial(dump_bytes_chunked, installation)
            )

        async def install_delete(
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            user: Annotated[User, Depends(framework.get_user)],
            id: str,
        ):
            installation_db = await get_installation(session, id, user.id)

            rmtree(installation_db.path)

            await session.delete(installation_db)
            await session.commit()

        super().get("/resolve/")(resolve)
        super().post("/products/")(fetch)
        super().post("/generators/")(generate)
        super().post("/installations/")(install_post)
        super().patch("/installations/{id}")(install_patch)
        super().put("/installations/{id}")(install_put)
        super().get("/installations/{id}")(install_get)
        super().delete("/installations/{id}")(install_delete)
