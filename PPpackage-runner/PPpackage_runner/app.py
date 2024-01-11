from contextlib import asynccontextmanager

from PPpackage_runner.database import User
from PPpackage_runner.endpoints.command import command
from PPpackage_runner.endpoints.run.dockerfile import run_dockerfile
from PPpackage_runner.endpoints.run.tag import run_tag
from PPpackage_runner.framework import framework
from PPpackage_runner.settings import Settings, settings
from PPpackage_runner.user import create_user_kwargs, create_user_response
from PPpackage_runner.utils import State, create_config
from PPpackage_utils.server import Server
from PPpackage_utils.utils import TemporaryDirectory


@asynccontextmanager
async def lifespan(settings: Settings):
    with TemporaryDirectory() as bundle_path, TemporaryDirectory() as crun_root_path:
        await create_config(bundle_path)

        yield State(bundle_path, crun_root_path)


app = Server(
    settings,
    framework,
    settings.database_url,
    lifespan,
    User,
    create_user_kwargs,
    create_user_response,
)

app.post("/run/tag")(run_tag)
app.post("/run/dockerfile")(run_dockerfile)
app.post("/command")(command)
