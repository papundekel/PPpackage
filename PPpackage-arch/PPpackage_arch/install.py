from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import MutableMapping
from io import TextIOWrapper
from pathlib import Path

from httpx import AsyncClient as HTTPClient
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Product
from PPpackage_utils.http_stream import HTTPResponseReader
from PPpackage_utils.pipe import (
    pipe_read_line_maybe,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.utils import (
    TemporaryDirectory,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
    movetree,
)

from .settings import Settings
from .utils import State, get_cache_paths


async def install_manager_command(
    debug: bool,
    pipe_to_fakealpm: TextIOWrapper,
    pipe_from_fakealpm: TextIOWrapper,
    runner_client: HTTPClient,
    runner_token: str,
    runner_workdir_path: Path,
):
    relative_path = pipe_read_string(debug, "PPpackage-arch", pipe_from_fakealpm)
    command = pipe_read_string(debug, "PPpackage-arch", pipe_from_fakealpm)
    args = pipe_read_strings(debug, "PPpackage-arch", pipe_from_fakealpm)

    with TemporaryPipe(runner_workdir_path) as pipe_hook_path:
        async with TaskGroup() as group:
            task = group.create_task(
                runner_client.post(
                    "http://localhost/command",
                    headers={"Authorization": f"Bearer {runner_token}"},
                    params={
                        "image_relative_path": str(relative_path),
                        "pipe_relative_path": str(
                            pipe_hook_path.relative_to(runner_workdir_path)
                        ),
                        "command": command,
                        "args": list(args),
                    },
                )
            )

        pipe_write_string(
            debug, "PPpackage-arch", pipe_to_fakealpm, str(pipe_hook_path)
        )

    reader = HTTPResponseReader(task.result())

    return_value = await reader.load_one(int)

    pipe_write_int(debug, "PPpackage-arch", pipe_to_fakealpm, return_value)


def create_environment(
    environment: MutableMapping[str, str],
    pipe_from_fakealpm_path: Path,
    pipe_to_fakealpm_path: Path,
    runner_workdir_path: Path,
    destination_path: Path,
):
    environment["LD_LIBRARY_PATH"] += ":/usr/share/libalpm-pp/usr/lib/"
    environment[
        "LD_PRELOAD"
    ] += f":PPpackage-arch/fakealpm/build/install/lib/libfakealpm.so"
    environment["PP_PIPE_FROM_FAKEALPM_PATH"] = str(pipe_from_fakealpm_path)
    environment["PP_PIPE_TO_FAKEALPM_PATH"] = str(pipe_to_fakealpm_path)
    environment["PP_RUNNER_WORKDIR_RELATIVE_PATH"] = str(
        destination_path.relative_to(runner_workdir_path)
    )


DATABASE_PATH_RELATIVE = Path("var") / "lib" / "pacman"


async def install(
    settings: Settings,
    state: State,
    installation_path: Path,
    product: Product,
):
    _, cache_path = get_cache_paths(settings.cache_path)

    runner_workdir_path = settings.runner_workdir_path

    with TemporaryDirectory(runner_workdir_path) as destination_path:
        movetree(installation_path, destination_path)

        database_path = destination_path / DATABASE_PATH_RELATIVE

        ensure_dir_exists(database_path)

        with (
            TemporaryPipe() as pipe_from_fakealpm_path,
            TemporaryPipe() as pipe_to_fakealpm_path,
        ):
            async with fakeroot(settings.debug) as environment:
                create_environment(
                    environment,
                    pipe_from_fakealpm_path,
                    pipe_to_fakealpm_path,
                    runner_workdir_path,
                    destination_path,
                )

                process = await create_subprocess_exec(
                    "pacman",
                    "--noconfirm",
                    "--needed",
                    "--dbpath",
                    str(database_path),
                    "--cachedir",
                    str(cache_path),
                    "--root",
                    str(destination_path),
                    "--upgrade",
                    "--nodeps",
                    "--nodeps",
                    *[
                        str(
                            cache_path
                            / f"{product.name}-{product.version}-{product.product_id}.pkg.tar.zst"
                        )
                    ],
                    stdin=DEVNULL,
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                    env=environment,
                )

                with (
                    open(pipe_from_fakealpm_path, "r") as pipe_from_fakealpm,
                    open(pipe_to_fakealpm_path, "w") as pipe_to_fakealpm,
                ):
                    while True:
                        header = pipe_read_line_maybe(
                            settings.debug, "PPpackage-arch", pipe_from_fakealpm
                        )

                        if header is None:
                            break
                        elif header == "COMMAND":
                            await install_manager_command(
                                settings.debug,
                                pipe_to_fakealpm,
                                pipe_from_fakealpm,
                                state.runner_client,
                                settings.runner_token,
                                runner_workdir_path,
                            )
                        else:
                            raise Exception(
                                f"Unknown header: {header}", "PPpackage-arch"
                            )

            await asubprocess_wait(process, CommandException())

        movetree(destination_path, installation_path)
