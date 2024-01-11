from collections.abc import AsyncGenerator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from httpx import AsyncClient as HTTPClient

from .localsubmanager import LocalSubmanagerContext
from .remotesubmanager import RemoteSubmanager
from .schemes import LocalSubmanagerConfig, RemoteSubmanagerConfig
from .submanager import Submanager


@asynccontextmanager
async def Submanagers(
    meta_config: Mapping[str, RemoteSubmanagerConfig | LocalSubmanagerConfig]
) -> AsyncGenerator[Mapping[str, Submanager], None]:
    client: HTTPClient | None = None

    async with AsyncExitStack() as client_stack:
        submanagers = dict[str, Submanager]()

        async with AsyncExitStack() as stack:
            for submanager_name, config in meta_config.items():
                if isinstance(config, RemoteSubmanagerConfig):
                    if client is None:
                        client = await client_stack.enter_async_context(
                            HTTPClient(http2=True)
                        )

                    submanager = RemoteSubmanager(submanager_name, client, config)
                else:
                    submanager = await stack.enter_async_context(
                        LocalSubmanagerContext(submanager_name, config)
                    )

                submanagers[submanager_name] = submanager

            yield submanagers
