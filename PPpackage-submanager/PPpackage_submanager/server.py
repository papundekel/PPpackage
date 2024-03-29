from contextlib import asynccontextmanager
from logging import getLogger
from pathlib import Path
from tempfile import mkdtemp
from typing import Annotated, Generic, TypeVar

from asyncstdlib import chain as async_chain
from asyncstdlib import list as async_list
from fastapi import Depends, FastAPI, Request
from PPpackage_utils.stream import Reader, dump_bytes_chunked, dump_many, dump_one
from PPpackage_utils.tar import archive as tar_archive
from PPpackage_utils.tar import extract as tar_extract
from PPpackage_utils.utils import (
    TemporaryDirectory,
    ensure_dir_exists,
    make_async_iterable,
    rmtree,
)
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY

from .database import Installation, User, create_token, get_installation
from .dependencies import get_user, require_admin_token
from .interface import load_interface_module
from .schemes import (
    Dependency,
    Lock,
    Options,
    Package,
    Product,
    ProductIDAndInfo,
    UserCreated,
)
from .utils import HTTPRequestReader, StreamingResponse, get_session, get_state

RequirementType = TypeVar("RequirementType")

SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")


class SubmanagerPackageSettings(BaseSettings):
    submanager_package: str


submanager_package_settings = SubmanagerPackageSettings()  # type: ignore

interface = load_interface_module(submanager_package_settings.submanager_package)


class ServerSettings(interface.Settings):
    database_url: AnyUrl
    installations_path: Path
    build_context_workdir_path: Path

    model_config = SettingsConfigDict(env_nested_delimiter="__", case_sensitive=False)


settings = ServerSettings()


logger = getLogger(__name__)


@asynccontextmanager
async def load_tar_and_extract(reader: Reader, present: bool):
    if not present:
        yield None
        return

    tar_bytes = await reader.load_bytes_chunked()

    with TemporaryDirectory(settings.build_context_workdir_path) as destination_path:
        tar_extract(tar_bytes, destination_path)

        yield destination_path


class SubmanagerServer(FastAPI, Generic[SettingsType, StateType, RequirementType]):
    def __init__(self):
        @asynccontextmanager
        async def lifespan_wrap(app: FastAPI):
            engine = create_async_engine(
                str(settings.database_url), connect_args={"check_same_thread": False}
            )

            async with interface.lifespan(settings) as state:
                app.state.state = state
                app.state.engine = engine

                ensure_dir_exists(settings.installations_path)

                yield

                app.state.engine = None
                app.state.state = None

            await engine.dispose()

        async def create_user(session: Annotated[AsyncSession, Depends(get_session)]):
            logger.debug("Creating a user...")

            user_token_db = await create_token(session, admin=False)

            user_db = User(token_id=user_token_db.id)
            session.add(user_db)

            await session.commit()
            await session.refresh(user_token_db)
            await session.refresh(user_db)

            logger.debug("User created.")

            return UserCreated(token=user_token_db.token)

        async def update_database(
            state: Annotated[StateType, Depends(get_state)],
        ):
            logger.debug("Updating database...")

            await interface.update_database(
                settings,  # type: ignore
                state,
            )

            logger.debug("Database updated.")

            return "success"

        async def resolve(
            request: Request,
            state: Annotated[StateType, Depends(get_state)],
        ):
            logger.debug("Resolving...")

            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)  # type: ignore

            requirements_list = (
                reader.load_many(interface.Requirement)
                async for _ in reader.load_loop()
            )

            locks = reader.load_many(Lock)

            # TODO: figure out why we need to iterate the async iterable
            outputs = await async_list(
                interface.resolve(
                    settings,
                    state,
                    options,
                    requirements_list,
                    locks,
                )
            )

            logger.debug("Resolved.")

            return StreamingResponse(
                HTTP_200_OK, dump_many(make_async_iterable(outputs))
            )

        async def fetch(
            request: Request,
            state: Annotated[StateType, Depends(get_state)],
            package_name: str,
            package_version: str,
            installation_present: bool,
            generators_present: bool,
        ):
            logger.debug("Fetching...")

            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)  # type: ignore

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

            logger.debug("Fetched.")

            if isinstance(output, ProductIDAndInfo):
                return StreamingResponse(HTTP_200_OK, dump_one(output))
            else:
                return StreamingResponse(
                    HTTP_422_UNPROCESSABLE_ENTITY,
                    async_chain(
                        dump_many(output.requirements), dump_many(output.generators)
                    ),
                )

        async def generate(
            request: Request,
            state: Annotated[StateType, Depends(get_state)],
        ):
            logger.debug("Generating...")

            reader = HTTPRequestReader(request)

            options = await reader.load_one(Options)  # type: ignore
            products = reader.load_many(Product)
            generators = reader.load_many(str)

            with TemporaryDirectory() as destination_path:
                await interface.generate(
                    settings,  # type: ignore
                    state,
                    options,
                    products,
                    generators,
                    destination_path,
                )

                generators_bytes = tar_archive(destination_path)

            logger.debug("Generated.")

            return StreamingResponse(HTTP_200_OK, dump_bytes_chunked(generators_bytes))

        async def install_patch(
            state: Annotated[StateType, Depends(get_state)],
            session: Annotated[AsyncSession, Depends(get_session)],
            user: Annotated[User, Depends(get_user)],
            id: str,
            package_name: str,
            package_version: str,
            product_id: str,
        ):
            logger.debug(f"Installing {package_name} {package_version}...")

            installation_db = await get_installation(session, id, user.id)

            await interface.install(
                settings,  # type: ignore
                state,
                installation_db.path,
                Product(package_name, package_version, product_id),
            )

            logger.debug(f"Installed {package_name} {package_version}.")

        async def install_post(
            request: Request,
            session: Annotated[AsyncSession, Depends(get_session)],
            user: Annotated[User, Depends(get_user)],
        ):
            logger.debug("Creating installation...")

            reader = HTTPRequestReader(request)

            installation = await reader.load_bytes_chunked()

            installation_path = Path(mkdtemp(dir=settings.installations_path))

            tar_extract(installation, installation_path)

            installation_db = Installation(path=installation_path)
            installation_db.user = user
            session.add(installation_db)
            await session.commit()
            await session.refresh(installation_db)

            logger.debug(f"Installation {installation_db.id} created.")

            return str(installation_db.id)

        async def install_put(
            request: Request,
            session: Annotated[AsyncSession, Depends(get_session)],
            user: Annotated[User, Depends(get_user)],
            id: str,
        ):
            logger.debug(f"Replacing installation {id}...")

            reader = HTTPRequestReader(request)

            installation = await reader.load_bytes_chunked()

            installation_db = await get_installation(session, id, user.id)

            tar_extract(installation, installation_db.path)

            logger.debug(f"Installation {id} replaced.")

        async def install_get(
            session: Annotated[AsyncSession, Depends(get_session)],
            user: Annotated[User, Depends(get_user)],
            id: str,
        ):
            logger.debug(f"Sending installation {id}...")

            installation_db = await get_installation(session, id, user.id)

            installation = tar_archive(installation_db.path)

            logger.debug(f"Installation {id} sent.")

            return StreamingResponse(HTTP_200_OK, dump_bytes_chunked(installation))

        async def install_delete(
            session: Annotated[AsyncSession, Depends(get_session)],
            user: Annotated[User, Depends(get_user)],
            id: str,
        ):
            logger.debug(f"Deleting installation {id}...")

            installation_db = await get_installation(session, id, user.id)

            rmtree(installation_db.path)

            await session.delete(installation_db)
            await session.commit()

            logger.debug(f"Installation {id} deleted.")

        super().__init__(debug=True, lifespan=lifespan_wrap, redoc_url=None)

        super().post("/user", dependencies=[Depends(require_admin_token)])(create_user)
        super().post("/update-database", dependencies=[Depends(require_admin_token)])(
            update_database
        )
        super().post("/resolve")(resolve)
        super().post("/products")(fetch)
        super().post("/generators")(generate)
        super().post("/installations")(install_post)
        super().patch("/installations/{id}")(install_patch)
        super().put("/installations/{id}")(install_put)
        super().get("/installations/{id}")(install_get)
        super().delete("/installations/{id}")(install_delete)


server = SubmanagerServer()
