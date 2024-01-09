from contextlib import asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
from typing import Any

from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    generate_empty,
    handle_connection,
    run_server,
    update_database_noop,
)
from PPpackage_utils.utils import Installations, RunnerInfo

from .fetch import fetch
from .install import (
    install_delete,
    install_get,
    install_patch,
    install_post,
    install_put,
)
from .resolve import resolve
from .utils import State

PROGRAM_NAME = "PPpackage-PP"

CALLBACKS = SubmanagerCallbacks(
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


async def main(
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_info: RunnerInfo,
):
    await run_server(
        debug, PROGRAM_NAME, run_path, partial(lifetime, runner_info, cache_path)
    )
