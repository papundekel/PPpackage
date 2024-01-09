from contextlib import asynccontextmanager

from PPpackage_runner.database import UserDB
from PPpackage_runner.endpoints.command import command
from PPpackage_runner.endpoints.run.dockerfile import run_dockerfile
from PPpackage_runner.endpoints.run.tag import run_tag
from PPpackage_runner.endpoints.user import create_user_kwargs
from PPpackage_runner.framework import framework
from PPpackage_runner.settings import settings
from PPpackage_runner.utils import State, create_config
from PPpackage_utils.server import Server
from PPpackage_utils.utils import TemporaryDirectory
from sqlalchemy.ext.asyncio import AsyncEngine


@asynccontextmanager
async def lifespan(engine: AsyncEngine):
    with TemporaryDirectory() as bundle_path, TemporaryDirectory() as crun_root_path:
        await create_config(bundle_path)

        yield State(engine, bundle_path, crun_root_path)


app = Server(
    settings.debug,
    framework,
    settings.database_url,
    lifespan,
    UserDB,
    create_user_kwargs,
)

app.post("/run/tag")(run_tag)
app.post("/run/dockerfile")(run_dockerfile)
app.post("/command")(command)
