from asyncio import StreamReader, StreamWriter, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Iterable, Mapping
from io import TextIOWrapper
from pathlib import Path
from random import choices as random_choices
from sys import stderr
from typing import IO

from PPpackage_utils.io import (
    communicate_with_runner,
    pipe_read_line,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.parse import (
    dump_bytes_chunked,
    dump_many,
    dump_one,
    load_bytes_chunked,
    load_one,
)
from PPpackage_utils.utils import (
    MACHINE_ID_RELATIVE_PATH,
    MyException,
    RunnerRequestType,
    TarFileInMemoryWrite,
    TemporaryPipe,
    asubprocess_wait,
    create_tar_file,
    debug_redirect_stderr,
    read_machine_id,
    tar_append,
)

from .utils import NodeData, data_to_product


async def install_manager_command(
    debug: bool,
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    runner_reader: StreamReader,
    runner_writer: StreamWriter,
    runner_workdir_path: Path,
):
    await dump_one(debug, runner_writer, RunnerRequestType.COMMAND)

    relative_path = pipe_read_string(debug, "PPpackage", pipe_from_sub)
    await dump_one(debug, runner_writer, relative_path)

    command = pipe_read_string(debug, "PPpackage", pipe_from_sub)
    await dump_one(debug, runner_writer, command)

    args = pipe_read_strings(debug, "PPpackage", pipe_from_sub)
    await dump_many(debug, runner_writer, args)

    with TemporaryPipe(runner_workdir_path) as pipe_hook_path:
        pipe_write_string(debug, "PPpackage", pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        await dump_one(
            debug,
            runner_writer,
            pipe_hook_path.relative_to(runner_workdir_path),
        )

        return_value = await load_one(debug, runner_reader, int)

        pipe_write_int(debug, "PPpackage", pipe_to_sub, return_value)
        pipe_to_sub.flush()


async def install_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    runner_reader: StreamReader,
    runner_writer: StreamWriter,
    runner_workdir_path: Path,
    generation: Iterable[tuple[str, NodeData]],
    old_installation: memoryview,
) -> memoryview:
    stderr.write(f"{manager}:\n")
    for package_name, _ in sorted(generation, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")

    with TemporaryPipe() as pipe_from_sub_path, TemporaryPipe() as pipe_to_sub_path:
        process = await create_subprocess_exec(
            f"PPpackage-{manager}",
            "--debug" if debug else "--no-debug",
            "install",
            str(cache_path),
            str(pipe_from_sub_path),
            str(pipe_to_sub_path),
            str(runner_workdir_path),
            stdin=PIPE,
            stdout=PIPE,
            stderr=debug_redirect_stderr(debug),
        )

        assert process.stdin is not None
        assert process.stdout is not None

        await dump_bytes_chunked(debug, process.stdin, old_installation)

        products = (
            data_to_product(package_name, data) for package_name, data in generation
        )

        await dump_many(debug, process.stdin, products)

        process.stdin.close()
        await process.stdin.wait_closed()

        with open(pipe_from_sub_path, "r", encoding="ascii") as pipe_from_sub:
            with open(pipe_to_sub_path, "w", encoding="ascii") as pipe_to_sub:
                while True:
                    header = pipe_read_line(debug, "PPpackage", pipe_from_sub)

                    if header == "END":
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            debug,
                            pipe_to_sub,
                            pipe_from_sub,
                            runner_reader,
                            runner_writer,
                            runner_workdir_path,
                        )
                    else:
                        raise MyException(
                            f"Invalid hook header from {manager} `{header}`."
                        )

        new_installation = await load_bytes_chunked(debug, process.stdout)

        await asubprocess_wait(process, f"Error in {manager}'s install.")

        return new_installation


def generate_machine_id(file: IO[bytes]):
    content_string = (
        "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
    )

    file.write(content_string.encode())


async def install(
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdir_path: Path,
    installation: memoryview,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    machine_id = read_machine_id(Path("/") / MACHINE_ID_RELATIVE_PATH)

    async with communicate_with_runner(debug, runner_path) as (
        runner_reader,
        runner_writer,
    ):
        await dump_one(debug, runner_writer, machine_id)

        for manager_to_generation in generations:
            for manager, generation in manager_to_generation.items():
                installation = await install_manager(
                    debug,
                    manager,
                    cache_path,
                    runner_reader,
                    runner_writer,
                    runner_workdir_path,
                    generation,
                    installation,
                )

    with TarFileInMemoryWrite() as tar:
        with create_tar_file(tar, MACHINE_ID_RELATIVE_PATH) as file:
            generate_machine_id(file)

        tar_append(installation, tar)

    return installation
