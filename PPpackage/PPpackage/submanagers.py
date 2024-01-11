from collections.abc import AsyncGenerator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager

from httpx import AsyncClient as HTTPClient
from pydantic import HttpUrl

from .localsubmanager import LocalSubmanagerContext
from .remotesubmanager import RemoteSubmanager
from .schemes import SubmanagerLocalConfig
from .submanager import Submanager


@asynccontextmanager
async def Submanagers(
    meta_config: Mapping[str, HttpUrl | SubmanagerLocalConfig]
) -> AsyncGenerator[Mapping[str, Submanager], None]:
    async with HTTPClient() as client:
        submanagers = dict[str, Submanager]()

        async with AsyncExitStack() as stack:
            for submanager_name, config in meta_config.items():
                if isinstance(config, HttpUrl):
                    submanager = RemoteSubmanager(submanager_name, client, config)
                else:
                    submanager = await stack.enter_async_context(
                        LocalSubmanagerContext(submanager_name, config)
                    )

                submanagers[submanager_name] = submanager

            yield submanagers
