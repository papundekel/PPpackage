from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Annotated, Any, AsyncContextManager, Generic, TypeVar

from fastapi import Depends, Request
from PPpackage_utils.http_stream import HTTPReader
from PPpackage_utils.server import (
    Framework,
    Server,
    State,
    StreamingResponse,
    TokenBase,
    UserBase,
)
from PPpackage_utils.stream import dump_bytes_chunked, dump_many_async
from PPpackage_utils.tar import create_empty as create_empty_tar
from pydantic import AnyUrl
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.status import HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY

from .schemes import (
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
)

RequirementTypeType = TypeVar("RequirementTypeType")
StateTypeType = TypeVar("StateTypeType", bound=State)
UserType = TypeVar("UserType", bound=UserBase)

UpdateDatabaseCallbackType = Callable[[bool, StateTypeType, Path], Awaitable[None]]
ResolveCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        AsyncIterable[AsyncIterable[RequirementTypeType]],
    ],
    AsyncIterable[ResolutionGraph],
]
FetchCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        Package,
        AsyncIterable[Dependency],
        memoryview | None,
        memoryview | None,
    ],
    Awaitable[PackageIDAndInfo | AsyncIterable[str]],
]

GenerateCallbackType = Callable[
    [
        bool,
        StateTypeType,
        Path,
        Any,
        AsyncIterable[Product],
        AsyncIterable[str],
    ],
    Awaitable[memoryview],
]
InstallPATCHCallbackType = Callable[
    [bool, StateTypeType, UserType, Path, str, Product],
    Awaitable[None],
]
InstallPOSTCallbackType = Callable[
    [bool, StateTypeType, UserType, memoryview], Awaitable[str]
]
InstallPUTCallbackType = Callable[
    [bool, StateTypeType, UserType, str, memoryview], Awaitable[None]
]
InstallGETCallbackType = Callable[
    [bool, StateTypeType, UserType, str], Awaitable[memoryview]
]
InstallDELETECallbackType = Callable[
    [bool, StateTypeType, UserType, str], Awaitable[None]
]


async def generate_empty(
    debug: bool,
    data: Any,
    cache_path: Path,
    options: Any,
    products: AsyncIterable[Product],
    generators: AsyncIterable[str],
) -> memoryview:
    async for _ in products:
        pass

    async for _ in generators:
        pass

    return create_empty_tar()


@contextmanager
def noop_session_lifetime(debug: bool, data: Any):
    yield None


async def update_database_noop(debug: bool, data: Any, cache_path: Path) -> None:
    pass


TokenDBType = TypeVar("TokenDBType", bound=TokenBase)
UserDBType = TypeVar("UserDBType", bound=UserBase)


class Submanager(
    Server[StateTypeType, TokenDBType, UserType, UserDBType],
    Generic[RequirementTypeType, StateTypeType, TokenDBType, UserType, UserDBType],
):
    def __init__(
        self,
        debug: bool,
        framework: Framework,
        database_url: AnyUrl,
        lifespan: Callable[[AsyncEngine], AsyncContextManager[Any]],
        UserDB: type[UserDBType],
        create_user_kwargs: Callable[[], Mapping[str, Any]],
        cache_path: Path,
        update_database_callback: UpdateDatabaseCallbackType[StateTypeType],
        resolve_callback: ResolveCallbackType[StateTypeType, RequirementTypeType],
        fetch_callback: FetchCallbackType[StateTypeType],
        generate_callback: GenerateCallbackType[StateTypeType],
        install_patch_callback: InstallPATCHCallbackType[StateTypeType, UserType],
        install_post_callback: InstallPOSTCallbackType[StateTypeType, UserType],
        install_put_callback: InstallPUTCallbackType[StateTypeType, UserType],
        install_get_callback: InstallGETCallbackType[StateTypeType, UserType],
        install_delete_callback: InstallDELETECallbackType[StateTypeType, UserType],
        RequirementType: type[RequirementTypeType],
    ):
        super().__init__(
            debug, framework, database_url, lifespan, UserDB, create_user_kwargs
        )

        async def resolve(
            request: Request,
            state: Annotated[StateTypeType, Depends(framework.get_state)],
        ):
            reader = HTTPReader(request)

            options = await reader.load_one(Options)

            requirements_list = (
                reader.load_many(RequirementType) async for _ in reader.load_loop()
            )

            output = resolve_callback(
                debug, state, cache_path, options, requirements_list
            )

            return StreamingResponse(HTTP_200_OK, partial(dump_many_async, output))

        async def fetch(
            request: Request,
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            package_name: str,
            package_version: str,
            installation_present: bool,
            generators_present: bool,
        ):
            reader = HTTPReader(request)

            options = await reader.load_one(Options)
            dependencies = reader.load_many(Dependency)
            installation = (
                await reader.load_bytes_chunked() if installation_present else None
            )
            generators = (
                await reader.load_bytes_chunked() if generators_present else None
            )

            output = await fetch_callback(
                debug,
                state,
                cache_path,
                options,
                Package(package_name, package_version),
                dependencies,
                installation,
                generators,
            )

            if not isinstance(output, PackageIDAndInfo):
                return StreamingResponse(
                    HTTP_422_UNPROCESSABLE_ENTITY, partial(dump_many_async, output)
                )

            return output

        async def generate(
            request: Request,
            state: Annotated[StateTypeType, Depends(framework.get_state)],
        ):
            reader = HTTPReader(request)

            options = await reader.load_one(Options)
            products = reader.load_many(Product)
            generators = reader.load_many(str)

            generators = await generate_callback(
                debug, state, cache_path, options, products, generators
            )

            return StreamingResponse(
                HTTP_200_OK, partial(dump_bytes_chunked, generators)
            )

        async def install_patch(
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            user: Annotated[UserType, Depends(framework.get_user)],
            id: str,
            package_name: str,
            package_version: str,
            product_id: str,
        ):
            await install_patch_callback(
                debug,
                state,
                user,
                cache_path,
                id,
                Product(package_name, package_version, product_id),
            )

        async def install_post(
            request: Request,
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            user: Annotated[UserType, Depends(framework.get_user)],
        ):
            reader = HTTPReader(request)

            installation = await reader.load_bytes_chunked()

            id = await install_post_callback(debug, state, user, installation)

            return id

        async def install_put(
            request: Request,
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            user: Annotated[UserType, Depends(framework.get_user)],
            id: str,
        ):
            reader = HTTPReader(request)

            installation = await reader.load_bytes_chunked()

            await install_put_callback(debug, state, user, id, installation)

        async def install_get(
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            user: Annotated[UserType, Depends(framework.get_user)],
            id: str,
        ):
            installation = await install_get_callback(debug, state, user, id)

            return StreamingResponse(
                HTTP_200_OK, partial(dump_bytes_chunked, installation)
            )

        async def install_delete(
            state: Annotated[StateTypeType, Depends(framework.get_state)],
            user: Annotated[UserType, Depends(framework.get_user)],
            id: str,
        ):
            await install_delete_callback(debug, state, user, id)

        super().get("/resolve/")(resolve)
        super().post("/products/")(fetch)
        super().post("/generators/")(generate)
        super().post("/installations/")(install_post)
        super().patch("/installations/{id}")(install_patch)
        super().put("/installations/{id}")(install_put)
        super().get("/installations/{id}")(install_get)
        super().delete("/installations/{id}")(install_delete)
