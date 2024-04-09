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


@asynccontextmanager
async def Repositories(
    drivers: Mapping[str, RepositoryDriverConfig],
    repositories: Iterable[RemoteRepositoryConfig | LocalRepositoryConfig],
) -> AsyncGenerator[Mapping[str, Repository], None]:
    client: HTTPClient | None = None

    async with AsyncExitStack() as client_stack:
        submanagers = dict[str, Repository]()

        for repository in repositories:
            if isinstance(repository, RemoteRepositoryConfig):
                if client is None:
                    client = await client_stack.enter_async_context(
                        HTTPClient(http2=True)
                    )

                submanager = RemoteRepository(repository, client)
            else:
                submanager = LocalRepository(repository, drivers)

            submanagers["TODO"] = submanager

        yield submanagers
