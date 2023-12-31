from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import MutableMapping
from io import TextIOWrapper
from pathlib import Path
from shutil import rmtree
from sys import stderr
from tempfile import mkdtemp

from PPpackage_utils.io import (
    pipe_read_line_maybe,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.parse import Product, dump_many, dump_one, load_one
from PPpackage_utils.utils import (
    RunnerRequestType,
    SubmanagerCommandFailure,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
    tar_archive,
    tar_extract,
)

from .utils import RunnerConnection, get_cache_paths


async def install_manager_command(
    debug: bool,
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    runner_connection: RunnerConnection,
):
    await dump_one(debug, runner_connection.writer, RunnerRequestType.COMMAND)

    relative_path = pipe_read_string(debug, "PPpackage-arch", pipe_from_sub)
    await dump_one(debug, runner_connection.writer, relative_path)

    command = pipe_read_string(debug, "PPpackage-arch", pipe_from_sub)
    await dump_one(debug, runner_connection.writer, command)

    args = pipe_read_strings(debug, "PPpackage-arch", pipe_from_sub)
    await dump_many(debug, runner_connection.writer, args)

    with TemporaryPipe(runner_connection.workdir_path) as pipe_hook_path:
        pipe_write_string(debug, "PPpackage-arch", pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        await dump_one(
            debug,
            runner_connection.writer,
            pipe_hook_path.relative_to(runner_connection.workdir_path),
        )

        return_value = await load_one(debug, runner_connection.reader, int)

        pipe_write_int(debug, "PPpackage-arch", pipe_to_sub, return_value)
        pipe_to_sub.flush()


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


def get_destination_path(runner_connection: RunnerConnection, id: str):
    destination_path = runner_connection.workdir_path / Path(id)

    if not destination_path.exists():
        raise SubmanagerCommandFailure

    return destination_path


async def install_patch(
    debug: bool,
    runner_connection: RunnerConnection,
    cache_path: Path,
    id: str,
    product: Product,
):
    _, cache_path = get_cache_paths(cache_path)

    destination_path = get_destination_path(runner_connection, id)

    database_path = destination_path / DATABASE_PATH_RELATIVE

    ensure_dir_exists(database_path)

    with (
        TemporaryPipe() as pipe_from_fakealpm_path,
        TemporaryPipe() as pipe_to_fakealpm_path,
    ):
        async with fakeroot(debug) as environment:
            create_environment(
                environment,
                pipe_from_fakealpm_path,
                pipe_to_fakealpm_path,
                runner_connection.workdir_path,
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
                        debug, "PPpackage-arch", pipe_from_fakealpm
                    )

                    if header is None:
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            debug,
                            pipe_to_fakealpm,
                            pipe_from_fakealpm,
                            runner_connection,
                        )
                    else:
                        raise Exception(
                            f"Unknown header: {header}", "PPpackage-arch", stderr
                        )

        await asubprocess_wait(process, SubmanagerCommandFailure())


async def install_post(
    debug: bool,
    connection: RunnerConnection,
    new_directory: memoryview,
) -> str:
    destination_path = Path(mkdtemp(dir=Path(connection.workdir_path)))

    tar_extract(new_directory, destination_path)

    return str(destination_path.relative_to(connection.workdir_path))


async def install_put(
    debug: bool,
    connection: RunnerConnection,
    id: str,
    new_directory: memoryview,
):
    destination_path = get_destination_path(connection, id)

    tar_extract(new_directory, destination_path)


async def install_get(debug: bool, connection: RunnerConnection, id: str) -> memoryview:
    destination_path = get_destination_path(connection, id)

    return tar_archive(destination_path)


async def install_delete(debug: bool, connection: RunnerConnection, id: str):
    destination_path = get_destination_path(connection, id)

    rmtree(destination_path)
