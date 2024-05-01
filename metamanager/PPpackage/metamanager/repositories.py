from collections.abc import AsyncGenerator, Iterable, Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from anysqlite import connect as sqlite_connect
from hishel import AsyncCacheClient as HTTPClient
from hishel import AsyncSQLiteStorage

from .localrepository import LocalRepository
from .remoterepository import RemoteRepository
from .repository import Repository, RepositoryInterface
from .schemes import (
    LocalRepositoryConfig,
    RemoteRepositoryConfig,
    RepositoryDriverConfig,
)


async def create_repository(
    client_stack: AsyncExitStack,
    client: HTTPClient | None,
    repository_config: LocalRepositoryConfig | RemoteRepositoryConfig,
    drivers: Mapping[str, RepositoryDriverConfig],
) -> RepositoryInterface:
    if isinstance(repository_config, RemoteRepositoryConfig):
        if client is None:
            client = await client_stack.enter_async_context(
                HTTPClient(
                    http2=True,
                    storage=AsyncSQLiteStorage(
                        connection=await sqlite_connect(
                            repository_config.cache_path / "db.sqlite"
                        )
                    ),
                )
            )

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
            await Repository.create(
                config,
                await create_repository(client_stack, client, config, drivers),
            )
            for config in repository_configs
        ]
