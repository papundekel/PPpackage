from collections.abc import Mapping
from contextlib import asynccontextmanager

from PPpackage_submanager.submanager import (
    Submanager,
    generate_empty,
    update_database_noop,
)
from PPpackage_utils.server import Framework
from sqlalchemy.ext.asyncio import AsyncEngine

from .database import TokenDB, User, UserDB
from .fetch import fetch
from .install import (
    install_delete,
    install_get,
    install_patch,
    install_post,
    install_put,
)
from .resolve import resolve
from .settings import settings
from .utils import State

framework = Framework(TokenDB, User)


@asynccontextmanager
async def lifespan(engine: AsyncEngine):
    yield State(engine)


def create_user_kwargs() -> Mapping[str, str]:
    return {}


app = Submanager(
    settings.debug,
    framework,
    settings.database_url,
    lifespan,
    UserDB,
    create_user_kwargs,
    settings.cache_path,
    update_database_noop,
    resolve,
    fetch,
    generate_empty,
    install_patch,
    install_post,
    install_put,
    install_get,
    install_delete,
    str,
)
