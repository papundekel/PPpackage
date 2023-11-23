from asyncio import StreamReader, StreamWriter, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable, Mapping
from io import TextIOWrapper
from os import listdir
from pathlib import Path
from random import choices as random_choices
from shutil import move
from sys import stderr
from xml.dom import Node

from PPpackage_utils.io import (
    communicate_with_daemon,
    pipe_read_line,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.parse import Product, dump_many, dump_one, load_one
from PPpackage_utils.utils import (
    MACHINE_ID_RELATIVE_PATH,
    MyException,
    RunnerRequestType,
    TemporaryPipe,
    asubprocess_wait,
    debug_redirect_stderr,
    read_machine_id,
)

from .utils import NodeData, data_to_product


async def install_manager_command(
    debug: bool,
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
):
    await dump_one(debug, daemon_writer, RunnerRequestType.COMMAND)
    await dump_one(debug, daemon_writer, destination_relative_path)

    command = pipe_read_string(debug, "PPpackage", pipe_from_sub)
    await dump_one(debug, daemon_writer, command)

    args = pipe_read_strings(debug, "PPpackage", pipe_from_sub)
    await dump_many(debug, daemon_writer, args)

    with TemporaryPipe(daemon_workdir_path) as pipe_hook_path:
        pipe_write_string(debug, "PPpackage", pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        await dump_one(
            debug,
            daemon_writer,
            pipe_hook_path.relative_to(daemon_workdir_path),
        )

        return_value = await load_one(debug, daemon_reader, int)

        pipe_write_int(debug, "PPpackage", pipe_to_sub, return_value)
        pipe_to_sub.flush()


async def install_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    generation: Iterable[tuple[str, NodeData]],
) -> None:
    with TemporaryPipe() as pipe_from_sub_path, TemporaryPipe() as pipe_to_sub_path:
        process = await create_subprocess_exec(
            f"PPpackage-{manager}",
            "--debug" if debug else "--no-debug",
            "install",
            str(cache_path),
            str(daemon_workdir_path / destination_relative_path),
            str(pipe_from_sub_path),
            str(pipe_to_sub_path),
            stdin=PIPE,
            stdout=DEVNULL,
            stderr=debug_redirect_stderr(debug),
        )

        assert process.stdin is not None

        await dump_many(
            debug,
            process.stdin,
            (data_to_product(package_name, data) for package_name, data in generation),
        )

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
                            daemon_reader,
                            daemon_writer,
                            daemon_workdir_path,
                            destination_relative_path,
                        )
                    else:
                        raise MyException(
                            f"Invalid hook header from {manager} `{header}`."
                        )

        await asubprocess_wait(process, f"Error in {manager}'s install.")


def generate_machine_id(machine_id_path: Path):
    if machine_id_path.exists():
        return

    machine_id_path.parent.mkdir(exist_ok=True, parents=True)

    with machine_id_path.open("w") as machine_id_file:
        machine_id_file.write(
            "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
        )


async def install(
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdir_path: Path,
    destination_path: Path,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> None:
    workdir_relative_path = Path("root")

    (runner_workdir_path / workdir_relative_path).mkdir(exist_ok=True, parents=True)

    for content in listdir(destination_path):
        move(
            destination_path / content,
            runner_workdir_path / workdir_relative_path / content,
        )

    generate_machine_id(
        runner_workdir_path / workdir_relative_path / MACHINE_ID_RELATIVE_PATH
    )

    machine_id = read_machine_id(Path("/") / MACHINE_ID_RELATIVE_PATH)

    async with communicate_with_daemon(debug, runner_path) as (
        daemon_reader,
        daemon_writer,
    ):
        await dump_one(debug, daemon_writer, machine_id)

        for manager_to_generation in generations:
            for manager, generation in manager_to_generation.items():
                await install_manager(
                    debug,
                    manager,
                    cache_path,
                    daemon_reader,
                    daemon_writer,
                    runner_workdir_path,
                    workdir_relative_path,
                    generation,
                )

        for content in listdir(runner_workdir_path / workdir_relative_path):
            move(
                runner_workdir_path / workdir_relative_path / content,
                destination_path / content,
            )
