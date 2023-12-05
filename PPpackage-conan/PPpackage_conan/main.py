from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    fetch_receive_discard,
    handle_connection,
    noop_session_lifetime,
    run_server,
)
from PPpackage_utils.utils import anoop

from .fetch import fetch_send
from .generate import generate
from .install import install
from .parse import Requirement
from .resolve import resolve
from .utils import get_package_paths

PROGRAM_NAME = "PPpackage-conan"
CALLBACKS = SubmanagerCallbacks(
    anoop,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate,
    install,
    Requirement,
)


@asynccontextmanager
async def lifetime(
    cache_path: Path,
    debug: bool,
):
    package_paths = get_package_paths()

    yield partial(
        handle_connection, cache_path, CALLBACKS, package_paths, noop_session_lifetime
    )


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
):
    await run_server(debug, PROGRAM_NAME, run_path, partial(lifetime, cache_path))
