from contextlib import asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
from typing import Any

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    fetch_receive_discard,
    generate_empty,
    handle_connection,
    run_server,
    update_database_noop,
)
from PPpackage_utils.utils import RunnerInfo

from .fetch import fetch_send
from .install import install, install_download, install_upload
from .resolve import resolve
from .utils import Installation

PROGRAM_NAME = "PPpackage-PP"

CALLBACKS = SubmanagerCallbacks(
    update_database_noop,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate_empty,
    install,
    install_upload,
    install_download,
    str,
)


@contextmanager
def session_lifetime(debug: bool, data: Any):
    yield Installation(memoryview(bytes()))


@asynccontextmanager
async def lifetime(
    runner_info: RunnerInfo,
    cache_path: Path,
    debug: bool,
):
    yield partial(
        handle_connection, cache_path, CALLBACKS, runner_info, session_lifetime
    )


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_info: RunnerInfo,
):
    await run_server(
        debug, PROGRAM_NAME, run_path, partial(lifetime, runner_info, cache_path)
    )
