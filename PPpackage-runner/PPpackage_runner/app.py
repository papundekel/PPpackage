from contextlib import asynccontextmanager

from PPpackage_utils.server import Server
from PPpackage_utils.utils import TemporaryDirectory

from .database import User
from .endpoints.command import command
from .endpoints.run.dockerfile import run_dockerfile
from .endpoints.run.tag import run_tag
from .framework import framework
from .settings import Settings, settings
from .user import create_user_kwargs, create_user_response
from .utils import State, create_config


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
