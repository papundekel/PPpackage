from asyncio import create_subprocess_exec
from asyncio import run as asyncio_run
from asyncio import sleep
from collections.abc import Callable
from contextlib import contextmanager
from multiprocessing import Process
from os import environ, getgid, getuid
from pathlib import Path
from subprocess import DEVNULL
from sys import stderr
from typing import Annotated, Optional

from PPpackage_utils.cli import AsyncTyper, run
from PPpackage_utils.utils import (
    MyException,
    TemporaryDirectory,
    asubprocess_wait,
    ensure_dir_exists,
)
from PPpackage_utils.validation import load_object
from typer import Option as TyperOption

from PPpackage.main import main as PPpackage
from PPpackage.schemes import Config

RUNNER_MANAGERS = {"arch", "PP"}
CONTAINER_RUN_PATH = "/mnt/PPpackage-run/"
CONTAINER_CACHE_PATH = "/workdir/cache/"


async def container(
    containerizer: str,
    manager: str,
    debug: bool,
    run_path: Path,
    cache_path: Path,
    runner_path: Path,
    runner_workdirs_path: Path,
):
    additional_options = (
        [
            "--ulimit",
            "nofile=1024:1048576",
            "--mount",
            "type=bind,readonly,source=/etc/passwd,destination=/etc/passwd",
            "--mount",
            "type=bind,readonly,source=/etc/group,destination=/etc/group",
            "--user",
            f"{getuid()}:{getgid()}",
        ]
        if containerizer == "docker"
        else []
    )

    additional_mounts = (
        [
            "--mount",
            f"type=bind,source={runner_path},destination=/run/PPpackage-runner.sock",
            "--mount",
            f"type=bind,source={runner_workdirs_path},destination=/mnt/PPpackage-runner-workdirs/",
        ]
        if manager in RUNNER_MANAGERS
        else []
    )

    additional_command_args = (
        [
            "/run/PPpackage-runner.sock",
            "/mnt/PPpackage-runner-workdirs/",
        ]
        if manager in RUNNER_MANAGERS
        else []
    )

    process = await create_subprocess_exec(
        containerizer,
        "run",
        "--rm",
        *additional_options,
        "--mount",
        f"type=bind,source={run_path},destination={CONTAINER_RUN_PATH}",
        "--mount",
        f"type=bind,source={cache_path},destination={CONTAINER_CACHE_PATH}",
        *additional_mounts,
        f"docker.io/fackop/pppackage-{manager.lower()}",
        "python",
        "-m",
        f"PPpackage_{manager}",
        "--debug" if debug else "--no-debug",
        CONTAINER_RUN_PATH,
        CONTAINER_CACHE_PATH,
        *additional_command_args,
        stdin=DEVNULL,
        stdout=stderr,
        stderr=None,
    )

    await asubprocess_wait(
        process, MyException(f"Error while running {manager} in a container.")
    )


@contextmanager
def process_lifetime(main: Callable, *args):
    def process_main(*args):
        asyncio_run(main(*args))

    process = Process(target=process_main, args=args)
    process.start()

    try:
        yield
    finally:
        process.terminate()
        process.join()


async def wait_for_sockets(max_retries: int | None, *socket_paths: Path):
    tried_count = 0

    while any(not socket_path.exists() for socket_path in socket_paths):
        if max_retries is not None and tried_count >= max_retries:
            raise MyException("Timeout while waiting for sockets.")

        await sleep(0.1)
        tried_count += 1


app = AsyncTyper()


@app.command()
async def main_command(
    containerizer: str,
    cache_path: Path,
    destination_path: Path,
    generators_path: Annotated[Optional[Path], TyperOption("--generators")] = None,
    graph_path: Annotated[Optional[Path], TyperOption("--graph")] = None,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
):
    ensure_dir_exists(cache_path)
    if generators_path is not None:
        ensure_dir_exists(generators_path)
    ensure_dir_exists(destination_path)

    run_path = Path(environ["XDG_RUNTIME_DIR"])

    containerizer_socket_path = run_path / Path("podman") / Path("podman.sock")

    config_dict = {
        "submanagers": {
            "arch": {
                "package": "PPpackage_arch",
                "settings": {
                    "debug": debug,
                    "cache_path": cache_path / Path("arch"),
                    "containerizer_socket_path": containerizer_socket_path,
                    "containerizer_host_workdir_path": Path("/"),
                    "containerizer_container_workdir_path": Path("/"),
                },
            },
            "conan": {
                "package": "PPpackage_conan",
                "settings": {
                    "debug": debug,
                    "cache_path": cache_path / Path("conan"),
                },
            },
            "PP": {
                "package": "PPpackage_PP",
                "settings": {
                    "debug": debug,
                    "cache_path": cache_path / Path("PP"),
                    "containerizer_socket_path": containerizer_socket_path,
                },
            },
        }
    }

    config = load_object(Config, config_dict)

    await PPpackage(
        debug,
        do_update_database,
        config,
        destination_path,
        generators_path,
        graph_path,
        10,
    )


run(app, "PPpackage-run")
