from asyncio import create_subprocess_exec
from asyncio import run as asyncio_run
from asyncio import sleep
from collections.abc import Callable
from contextlib import ExitStack, contextmanager
from functools import partial
from multiprocessing import Process
from os import environ, getgid, getuid
from pathlib import Path
from subprocess import DEVNULL
from sys import stderr
from typing import Annotated

from PPpackage_runner.main import main as runner
from PPpackage_utils.submanager import AsyncTyper, run
from PPpackage_utils.utils import (
    RunnerInfo,
    TemporaryDirectory,
    asubprocess_wait,
    ensure_dir_exists,
)
from typer import Option as TyperOption

from PPpackage.main import main as PPpackage

RUNNER_MANAGERS = {"arch", "PP"}


async def docker(
    manager: str,
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_info: RunnerInfo,
):
    additional_mounts = (
        [
            "--mount",
            f"type=bind,source={runner_info.socket_path},destination=/run/PPpackage-runner.sock",
            "--mount",
            f"type=bind,source={runner_info.workdirs_path},destination=/mnt/PPpackage-runner-workdirs/",
        ]
        if manager in RUNNER_MANAGERS
        else []
    )

    additional_args = (
        [
            "/run/PPpackage-runner.sock",
            "/mnt/PPpackage-runner-workdirs/",
        ]
        if manager in RUNNER_MANAGERS
        else []
    )

    process = await create_subprocess_exec(
        "docker",
        "run",
        "--rm",
        "--ulimit",
        "nofile=1024:1048576",
        "--mount",
        "type=bind,readonly,source=/etc/passwd,destination=/etc/passwd",
        "--mount",
        "type=bind,readonly,source=/etc/group,destination=/etc/group",
        "--user",
        f"{getuid()}:{getgid()}",
        "--mount",
        f"type=bind,source={run_path},destination=/run/",
        "--mount",
        f"type=bind,source={cache_path},destination=/workdir/cache/",
        *additional_mounts,
        f"fackop/pppackage-{manager.lower()}",
        "python",
        "-m",
        f"PPpackage_{manager}",
        "--debug" if debug else "--no-debug",
        f"/run/",
        "/workdir/cache/",
        *additional_args,
        stdin=DEVNULL,
        stdout=stderr,
        stderr=None,
    )

    await asubprocess_wait(process, f"Error while running {manager} in docker.")


def process_main(main: Callable, *args):
    asyncio_run(main(*args))


@contextmanager
def process_lifetime(main: Callable, *args):
    process = Process(target=partial(process_main, main), args=args)
    process.start()

    try:
        yield
    finally:
        process.terminate()
        process.join()


async def wait_for_sockets(*socket_paths: Path):
    while any(not socket_path.exists() for socket_path in socket_paths):
        await sleep(0.1)


app = AsyncTyper()


@app.command()
async def main_command(
    mode: str,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
):
    if mode == "native":
        from PPpackage_arch.main import main as PPpackage_arch
        from PPpackage_conan.main import main as base_PPpackage_conan
        from PPpackage_PP.main import main as PPpackage_PP

        PPpackage_conan = (
            lambda debug, run_path, cache_path, *args: base_PPpackage_conan(
                debug, run_path, cache_path
            )
        )
    else:
        PPpackage_arch = partial(docker, "arch")
        PPpackage_conan = partial(docker, "conan")
        PPpackage_PP = partial(docker, "PP")

    SUBMANAGERS = {"arch": PPpackage_arch, "conan": PPpackage_conan, "PP": PPpackage_PP}

    run_path = Path(environ["XDG_RUNTIME_DIR"])

    ensure_dir_exists(cache_path)
    ensure_dir_exists(generators_path)
    ensure_dir_exists(destination_path)

    with TemporaryDirectory() as runner_workdirs_path:
        with process_lifetime(runner, debug, run_path, runner_workdirs_path):
            runner_path = run_path / "PPpackage-runner.sock"

            await wait_for_sockets(runner_path)

            with ExitStack() as exit_stack:
                submanager_socket_paths = {}

                for manager, main in SUBMANAGERS.items():
                    submanager_run_path = exit_stack.enter_context(
                        TemporaryDirectory(run_path)
                    )

                    exit_stack.enter_context(
                        process_lifetime(
                            main,
                            debug,
                            submanager_run_path,
                            cache_path,
                            RunnerInfo(runner_path, runner_workdirs_path),
                        ),
                    )

                    submanager_socket_paths[manager] = (
                        submanager_run_path / f"PPpackage-{manager}.sock"
                    )

                await wait_for_sockets(*submanager_socket_paths.values())

                await PPpackage(
                    debug,
                    do_update_database,
                    submanager_socket_paths,
                    generators_path,
                    destination_path,
                )


run(app, "PPpackage-run")
