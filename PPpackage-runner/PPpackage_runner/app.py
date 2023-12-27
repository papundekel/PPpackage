from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager

from fastapi import FastAPI
from PPpackage_runner.endpoints.command import command
from PPpackage_runner.endpoints.run.dockerfile import run_dockerfile
from PPpackage_runner.endpoints.run.tag import run_tag
from PPpackage_runner.endpoints.user import user
from PPpackage_runner.settings import DATABASE_URL, DEBUG
from PPpackage_runner.utils import State, create_config, framework
from PPpackage_utils.utils import TemporaryDirectory
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Server(FastAPI):
    def __init__(
        self, debug: bool, lifespan: Callable[[AsyncEngine], AsyncContextManager[Any]]
    ):
        @asynccontextmanager
        async def lifespan_wrap(app: FastAPI):
            engine = create_async_engine(
                DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
            )

            async with lifespan(engine) as state:
                app.state.state = state
                yield
                app.state.state = None

            await engine.dispose()

        super().__init__(debug=debug, lifespan=lifespan_wrap, redoc_url=None)


@asynccontextmanager
async def lifespan(engine: AsyncEngine):
    with TemporaryDirectory() as bundle_path, TemporaryDirectory() as crun_root_path:
        await create_config(bundle_path)

        yield State(engine, bundle_path, crun_root_path)


app = Server(DEBUG, lifespan)

app.post("/run/tag")(framework.create_endpoint(run_tag))
app.post("/run/dockerfile")(framework.create_endpoint(run_dockerfile))
app.post("/command")(framework.create_endpoint(command))
app.post("/user")(user)
