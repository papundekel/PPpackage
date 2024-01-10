from asyncio import Event, as_completed, create_subprocess_exec, get_running_loop
from asyncio import run as asyncio_run
from asyncio import sleep
from collections.abc import AsyncIterable, Callable
from contextlib import contextmanager
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
from hypercorn import Config
from hypercorn.asyncio import serve
from PPpackage_utils.cli import AsyncTyper, run
from PPpackage_utils.utils import (
    MyException,
    TemporaryDirectory,
    asubprocess_wait,
    ensure_dir_exists,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from typer import Option as TyperOption

# from PPpackage.main import main as PPpackage


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

    config = Config()
    config.bind = [f"unix:{socket_path}"]

    runner_set_environment(database_url, workdirs_path)

    from PPpackage_runner import settings

    reload_module(settings)
    from PPpackage_runner.app import app

    await serve(
        app,  # type: ignore
        config,
        mode="asgi",
        shutdown_trigger=shutdown_event.wait,  #  type: ignore
    )


async def runner_create_user(client: HTTPClient, token: str) -> str:
    response = await client.post(
        "http://localhost/user", headers={"Authorization": f"Bearer {token}"}
    )

    token = response.raise_for_status().json()

    if not isinstance(token, str):
        raise Exception(f"Invalid response from the server.\n{token}")

    return token


async def runner_create_users(
    client: HTTPClient, token: str, count: int
) -> AsyncIterable[str]:
    for task in as_completed([runner_create_user(client, token) for _ in range(count)]):
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
    # if containerizer == "native":
    #     from PPpackage_arch.main import main as PPpackage_arch
    #     from PPpackage_conan.main import main as base_PPpackage_conan
    #     from PPpackage_PP.main import main as PPpackage_PP

    #     PPpackage_conan = (
    #         lambda debug, run_path, cache_path, *args: base_PPpackage_conan(
    #             debug, run_path, cache_path
    #         )
    #     )
    # else:
    #     PPpackage_arch = partial(container, containerizer, "arch")
    #     PPpackage_conan = partial(container, containerizer, "conan")
    #     PPpackage_PP = partial(container, containerizer, "PP")

    # SUBMANAGERS = {"arch": PPpackage_arch, "conan": PPpackage_conan, "PP": PPpackage_PP}

    run_path = Path(environ["XDG_RUNTIME_DIR"])

    ensure_dir_exists(cache_path)
    if generators_path is not None:
        ensure_dir_exists(generators_path)
    ensure_dir_exists(destination_path)

    with (
        TemporaryDirectory() as runner_workdirs_path,
        TemporaryDirectory() as runner_db_dir_path,
    ):
        runner_path = run_path / RUNNER_SOCKET_NAME

        runner_database_url = f"sqlite+aiosqlite:///{runner_db_dir_path}/db.sqlite"

        runner_token = await runner_create_db(runner_database_url)

        with process_lifetime(
            runner, runner_path, runner_database_url, runner_workdirs_path
        ):
            async with HTTPClient(
                http2=True,
                transport=AsyncHTTPTransport(http2=True, uds=str(runner_path)),
            ) as client:
                async for token in runner_create_users(client, runner_token, 5):
                    print(token, file=stderr)

            await wait_for_sockets(wait_max_retries, runner_path)

            await sleep(1000)

            # with ExitStack() as exit_stack:
            #     submanager_socket_paths = {}

            #     for manager, main in SUBMANAGERS.items():
            #         submanager_run_path = exit_stack.enter_context(
            #             TemporaryDirectory(run_path)
            #         )

            #         exit_stack.enter_context(
            #             process_lifetime(
            #                 main,
            #                 debug,
            #                 submanager_run_path,
            #                 cache_path,
            #                 RunnerInfo(runner_path, runner_workdirs_path),
            #             ),
            #         )

            #         submanager_socket_paths[manager] = (
            #             submanager_run_path / f"PPpackage-{manager}.sock"
            #         )

            #     await wait_for_sockets(
            #         wait_max_retries, *submanager_socket_paths.values()
            #     )

            #     await PPpackage(
            #         debug,
            #         do_update_database,
            #         submanager_socket_paths,
            #         destination_path,
            #         generators_path,
            #         graph_path,
            #         10,
            #     )


run(app, "PPpackage-run")
