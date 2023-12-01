from asyncio import StreamReader, StreamWriter, create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable
from io import TextIOWrapper
from pathlib import Path
from sys import stderr

from PPpackage_utils.io import (
    communicate_with_runner,
    pipe_read_line,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.parse import Product, dump_many, dump_one, load_one
from PPpackage_utils.utils import (
    RunnerRequestType,
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
    TemporaryDirectory,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
    read_machine_id,
)

from .utils import get_cache_paths


async def install_manager_command(
    debug: bool,
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    runner_reader: StreamReader,
    runner_writer: StreamWriter,
    runner_workdir_path: Path,
):
    await dump_one(debug, runner_writer, RunnerRequestType.COMMAND)

    relative_path = pipe_read_string(debug, "PPpackage-arch", pipe_from_sub)
    await dump_one(debug, runner_writer, relative_path)

    command = pipe_read_string(debug, "PPpackage-arch", pipe_from_sub)
    await dump_one(debug, runner_writer, command)

    args = pipe_read_strings(debug, "PPpackage-arch", pipe_from_sub)
    await dump_many(debug, runner_writer, args)

    with TemporaryPipe(runner_workdir_path) as pipe_hook_path:
        pipe_write_string(debug, "PPpackage-arch", pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        await dump_one(
            debug,
            runner_writer,
            pipe_hook_path.relative_to(runner_workdir_path),
        )

        return_value = await load_one(debug, runner_reader, int)

        pipe_write_int(debug, "PPpackage-arch", pipe_to_sub, return_value)
        pipe_to_sub.flush()


async def install(
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdir_path: Path,
    old_directory: memoryview,
    products: AsyncIterable[Product],
) -> memoryview:
    _, cache_path = get_cache_paths(cache_path)
    database_path_relative = Path("var") / "lib" / "pacman"

    print("X", file=stderr)

    with TemporaryDirectory(runner_workdir_path) as destination_path:
        with TarFileInMemoryRead(old_directory) as old_tar:
            old_tar.extractall(destination_path)

        database_path = destination_path / database_path_relative

        ensure_dir_exists(database_path)

        machine_id = read_machine_id(Path("/"))

        async with communicate_with_runner(debug, runner_path, machine_id) as (
            runner_reader,
            runner_writer,
        ):
            with (
                TemporaryPipe() as pipe_from_fakealpm_path,
                TemporaryPipe() as pipe_to_fakealpm_path,
            ):
                async with fakeroot(debug) as environment:
                    environment["LD_LIBRARY_PATH"] += ":/usr/share/libalpm-pp/usr/lib/"
                    environment[
                        "LD_PRELOAD"
                    ] += f":fakealpm/build/install/lib/libfakealpm.so"
                    environment["PP_PIPE_FROM_FAKEALPM_PATH"] = str(
                        pipe_from_fakealpm_path
                    )
                    environment["PP_PIPE_TO_FAKEALPM_PATH"] = str(pipe_to_fakealpm_path)
                    environment["PP_RUNNER_WORKDIR_RELATIVE_PATH"] = str(
                        destination_path.relative_to(runner_workdir_path)
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
                        stderr=None,
                        env=environment,
                    )

                    print(pipe_from_fakealpm_path, pipe_to_fakealpm_path, file=stderr)

                    with (
                        open(pipe_from_fakealpm_path, "r") as pipe_from_fakealpm,
                        open(pipe_to_fakealpm_path, "w") as pipe_to_fakealpm,
                    ):
                        print("XXX", file=stderr)

                        while True:
                            header = pipe_read_line(
                                debug, "PPpackage-arch", pipe_from_fakealpm
                            )

                            if header == "COMMAND":
                                await install_manager_command(
                                    debug,
                                    pipe_to_fakealpm,
                                    pipe_from_fakealpm,
                                    runner_reader,
                                    runner_writer,
                                    runner_workdir_path,
                                )
                            else:
                                print(f"header: {header}", file=stderr)
                                break

                    await asubprocess_wait(process, "Error in `pacman -Udd`")

        with TarFileInMemoryWrite() as new_tar:
            new_tar.add(str(destination_path), "")

        return new_tar.data
