from contextlib import asynccontextmanager

from httpx import AsyncClient as HTTPClient
from httpx import AsyncHTTPTransport

from .settings import Settings
from .utils import State


@asynccontextmanager
async def lifespan(settings: Settings):
    async with HTTPClient(
        http2=True,
        transport=AsyncHTTPTransport(http2=True, uds=str(settings.runner_socket_path)),
    ) as runner_client:
        yield State(runner_client)
