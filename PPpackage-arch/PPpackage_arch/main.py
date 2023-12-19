from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from PPpackage_arch.utils import RunnerConnection
from PPpackage_utils.io import communicate_with_runner
from PPpackage_utils.submanager import (
    SubmanagerCallbacks,
    generate_empty,
    handle_connection,
    run_server,
)
from PPpackage_utils.utils import RunnerInfo

from .fetch import fetch
from .install import (
    install_delete,
    install_get,
    install_patch,
    install_post,
    install_put,
)
from .resolve import resolve
from .update_database import update_database

PROGRAM_NAME = "PPpackage-arch"

CALLBACKS = SubmanagerCallbacks(
    update_database,
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


@asynccontextmanager
async def lifetime(
    runner_info: RunnerInfo,
    cache_path: Path,
    debug: bool,
):
    async with communicate_with_runner(debug, runner_info) as (
        runner_reader,
        runner_writer,
        runner_workdir_path,
    ):
        yield partial(
            handle_connection,
            cache_path,
            CALLBACKS,
            RunnerConnection(runner_reader, runner_writer, runner_workdir_path),
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
