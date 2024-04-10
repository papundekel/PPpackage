from collections.abc import AsyncGenerator, Iterable, Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from httpx import AsyncClient as HTTPClient

from .localrepository import LocalRepository
from .remoterepository import RemoteRepository
from .repository import Repository
from .schemes import (
    LocalRepositoryConfig,
    RemoteRepositoryConfig,
    RepositoryDriverConfig,
)


async def create_repository(
    client: HTTPClient | None,
    client_stack: AsyncExitStack,
    repository_config: LocalRepositoryConfig | RemoteRepositoryConfig,
    drivers: Mapping[str, RepositoryDriverConfig],
) -> Repository:
    if isinstance(repository_config, RemoteRepositoryConfig):
        if client is None:
            client = await client_stack.enter_async_context(HTTPClient(http2=True))

        return RemoteRepository(repository_config, client)
    else:
        return LocalRepository(repository_config, drivers)


@asynccontextmanager
async def Repositories(
    drivers: Mapping[str, RepositoryDriverConfig],
    repository_configs: Iterable[RemoteRepositoryConfig | LocalRepositoryConfig],
) -> AsyncGenerator[Iterable[Repository], None]:
    client: HTTPClient | None = None

    async with AsyncExitStack() as client_stack:
        yield [
            await create_repository(client, client_stack, config, drivers)
            for config in repository_configs
        ]
