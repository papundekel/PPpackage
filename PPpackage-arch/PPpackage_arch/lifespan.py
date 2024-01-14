from contextlib import asynccontextmanager

from .settings import Settings


@asynccontextmanager
async def lifespan(settings: Settings):
    yield None
