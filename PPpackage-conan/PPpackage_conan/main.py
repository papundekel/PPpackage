from contextlib import asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
from typing import Any

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    handle_connection,
    run_server,
    update_database_noop,
)

from .fetch import fetch
from .generate import generate
from .install import install, install_download, install_upload
from .parse import Requirement
from .resolve import resolve
from .utils import Installation, get_package_paths

PROGRAM_NAME = "PPpackage-conan"
CALLBACKS = SubmanagerCallbacks(
    update_database_noop,
    resolve,
    fetch,
    generate,
    install,
    install_upload,
    install_download,
    Requirement,
)


@contextmanager
def session_lifetime(debug: bool, data: Any):
    yield Installation(memoryview(bytes()))


@asynccontextmanager
async def lifetime(
    cache_path: Path,
    debug: bool,
):
    package_paths = get_package_paths()

    yield partial(
        handle_connection, cache_path, CALLBACKS, package_paths, session_lifetime
    )


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
):
    await run_server(debug, PROGRAM_NAME, run_path, partial(lifetime, cache_path))
