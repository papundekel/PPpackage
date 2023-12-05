from contextlib import asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    fetch_receive_discard,
    generate_empty,
    handle_connection,
    noop_session_lifetime,
    run_server,
)
from PPpackage_utils.utils import RunnerInfo, anoop

from .fetch import fetch_send
from .install import install
from .resolve import resolve

PROGRAM_NAME = "PPpackage-PP"

CALLBACKS = SubmanagerCallbacks(
    anoop,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate_empty,
    install,
    str,
)


@asynccontextmanager
async def lifetime(
    runner_info: RunnerInfo,
    cache_path: Path,
    debug: bool,
):
    yield partial(
        handle_connection, cache_path, CALLBACKS, runner_info, noop_session_lifetime
    )


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_info: RunnerInfo,
):
    await run_server(
        debug,
        PROGRAM_NAME,
        run_path,
        partial(lifetime, runner_info, cache_path),
    )
