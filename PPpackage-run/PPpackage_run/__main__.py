from asyncio import Event, as_completed, create_subprocess_exec, get_running_loop
from asyncio import run as asyncio_run
from asyncio import sleep
from collections.abc import AsyncIterable, Callable
from contextlib import ExitStack, contextmanager
from importlib import reload as reload_module
from multiprocessing import Process
from os import environ, getgid, getuid
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL
from sys import stderr
from typing import Annotated, Optional

from httpx import AsyncClient as HTTPClient
from httpx import AsyncHTTPTransport
from hypercorn import Config as HTTPServerConfig
from hypercorn.asyncio import serve
from PPpackage_runner.schemes import UserResponse as RunnerUserResponse
from PPpackage_utils.cli import AsyncTyper, run
from PPpackage_utils.utils import (
    MyException,
    TemporaryDirectory,
    asubprocess_wait,
    ensure_dir_exists,
)
from PPpackage_utils.validation import load_from_bytes, load_object
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
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


RUNNER_SOCKET_NAME = Path("PPpackage-runner.sock")


def runner_set_environment(database_url: str, workdirs_path: Path):
    environ["DATABASE_URL"] = database_url
    environ["WORKDIRS_PATH"] = str(workdirs_path)


async def runner_create_db(database_url: str):
    env = environ.copy()

    runner_set_environment(database_url, Path("/"))

    from PPpackage_runner.framework import framework

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    token = await framework.create_admin_token(engine)

    await engine.dispose()

    environ.update(env)

    return token


async def runner(socket_path: Path, database_url: str, workdirs_path: Path):
    shutdown_event = Event()

    get_running_loop().add_signal_handler(SIGTERM, shutdown_event.set)

    config = HTTPServerConfig()
    config.bind = [f"unix:{socket_path}"]

    runner_set_environment(database_url, workdirs_path)

    from PPpackage_runner import settings

    reload_module(settings)
    from PPpackage_runner.app import app

    @contextmanager
    def socket_lifetime():
        yield
        socket_path.unlink()

    with socket_lifetime():
        await serve(
            app,  # type: ignore
            config,
            mode="asgi",
            shutdown_trigger=shutdown_event.wait,  #  type: ignore
        )


async def runner_create_user(
    client: HTTPClient, admin_token: str
) -> RunnerUserResponse:
    response = await client.post(
        "http://localhost/user", headers={"Authorization": f"Bearer {admin_token}"}
    )

    if not response.is_success:
        raise Exception(f"Error while creating a runner user.")

    response_bytes = await response.aread()

    user_response = load_from_bytes(RunnerUserResponse, response_bytes)

    return user_response


async def runner_create_users(
    runner_path: Path, token: str, count: int
) -> AsyncIterable[RunnerUserResponse]:
    async with HTTPClient(
        http2=True,
        transport=AsyncHTTPTransport(http2=True, uds=str(runner_path)),
    ) as client:
        for task in as_completed(
            [runner_create_user(client, token) for _ in range(count)]
        ):
            yield await task


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
    wait_max_retries: Optional[int] = None,
):
    run_path = Path(environ["XDG_RUNTIME_DIR"])

    ensure_dir_exists(cache_path)
    if generators_path is not None:
        ensure_dir_exists(generators_path)
    ensure_dir_exists(destination_path)

    with (
        TemporaryDirectory() as runner_workdirs_path,
        TemporaryDirectory() as runner_db_dir_path,
    ):
        runner_socket_path = run_path / RUNNER_SOCKET_NAME

        runner_database_url = f"sqlite+aiosqlite:///{runner_db_dir_path}/db.sqlite"

        runner_token = await runner_create_db(runner_database_url)

        with process_lifetime(
            runner, runner_socket_path, runner_database_url, runner_workdirs_path
        ):
            await wait_for_sockets(wait_max_retries, runner_socket_path)

            runner_responses = [
                runner_response
                async for runner_response in runner_create_users(
                    runner_socket_path, runner_token, 2
                )
            ]

            config_dict = {
                "submanagers": {
                    "arch": {
                        "package": "PPpackage_arch",
                        "settings": {
                            "debug": debug,
                            "cache_path": cache_path / Path("arch"),
                            "runner_socket_path": runner_socket_path,
                            "runner_token": runner_responses[0].token,
                            "runner_workdir_path": runner_workdirs_path
                            / runner_responses[0].workdir_relative_path,
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
                            "runner_socket_path": runner_socket_path,
                            "runner_token": runner_responses[1].token,
                            "runner_workdir_path": runner_workdirs_path
                            / runner_responses[1].workdir_relative_path,
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
