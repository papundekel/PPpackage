from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable, MutableMapping
from io import TextIOWrapper
from pathlib import Path
from sys import stderr

from PPpackage_utils.io import (
    pipe_read_line_maybe,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.parse import Product, dump_many, dump_one, load_one
from PPpackage_utils.utils import (
    MyException,
    RunnerRequestType,
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
    TemporaryDirectory,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
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
    environment["LD_PRELOAD"] += f":fakealpm/build/install/lib/libfakealpm.so"
    environment["PP_PIPE_FROM_FAKEALPM_PATH"] = str(pipe_from_fakealpm_path)
    environment["PP_PIPE_TO_FAKEALPM_PATH"] = str(pipe_to_fakealpm_path)
    environment["PP_RUNNER_WORKDIR_RELATIVE_PATH"] = str(
        destination_path.relative_to(runner_workdir_path)
    )


DATABASE_PATH_RELATIVE = Path("var") / "lib" / "pacman"


async def install(
    debug: bool,
    runner_connection: RunnerConnection,
    cache_path: Path,
    old_directory: memoryview,
    products: AsyncIterable[Product],
) -> memoryview:
    _, cache_path = get_cache_paths(cache_path)

    with TemporaryDirectory(runner_connection.workdir_path) as destination_path:
        with TarFileInMemoryRead(old_directory) as old_tar:
            old_tar.extractall(destination_path)

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
                        async for product in products
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
                            raise MyException(
                                f"Unknown header: {header}",
                                "PPpackage-arch",
                                stderr,
                            )

            await asubprocess_wait(process, "Error in `pacman -Udd`")

        with TarFileInMemoryWrite() as new_tar:
            new_tar.add(str(destination_path), "")

    return new_tar.data
