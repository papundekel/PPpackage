from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Iterable, Mapping
from pathlib import Path
from random import choices as random_choices
from sys import stderr
from typing import IO

from PPpackage_utils.parse import dump_bytes_chunked, dump_many, load_bytes_chunked
from PPpackage_utils.utils import (
    MACHINE_ID_RELATIVE_PATH,
    TarFileInMemoryWrite,
    TemporaryPipe,
    asubprocess_wait,
    create_tar_file,
    debug_redirect_stderr,
    tar_append,
)

from .utils import NodeData, data_to_product


async def install_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    runner_path: Path,
    runner_workdir_path: Path,
    generation: Iterable[tuple[str, NodeData]],
    old_installation: memoryview,
) -> memoryview:
    stderr.write(f"{manager}:\n")
    for package_name, _ in sorted(generation, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")

    process = await create_subprocess_exec(
        "python",
        "-m",
        f"PPpackage_{manager}",
        "--debug" if debug else "--no-debug",
        "install",
        str(cache_path),
        str(runner_path),
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

    for manager_to_generation in generations:
        for manager, generation in manager_to_generation.items():
            installation = await install_manager(
                debug,
                manager,
                cache_path,
                runner_path,
                runner_workdir_path,
                generation,
                installation,
            )

    with TarFileInMemoryWrite() as tar:
        with create_tar_file(tar, MACHINE_ID_RELATIVE_PATH) as file:
            generate_machine_id(file)

        tar_append(installation, tar)

    return installation
