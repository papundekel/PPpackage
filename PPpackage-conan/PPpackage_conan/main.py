from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    handle_connection,
    run_server,
    update_database_noop,
)

from .fetch import fetch
from .generate import generate
from .install import (
    install_delete,
    install_get,
    install_patch,
    install_post,
    install_put,
)
from .parse import Requirement
from .resolve import resolve
from .utils import create_data

PROGRAM_NAME = "PPpackage-conan"
CALLBACKS = SubmanagerCallbacks(
    update_database_noop,
    resolve,
    fetch,
    generate,
    install_patch,
    install_post,
    install_put,
    install_get,
    install_delete,
    Requirement,
)


@asynccontextmanager
async def lifetime(
    cache_path: Path,
    debug: bool,
):
    data = create_data()

    yield partial(handle_connection, cache_path, CALLBACKS, data)


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
):
    await run_server(debug, PROGRAM_NAME, run_path, partial(lifetime, cache_path))
