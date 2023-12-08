from asyncio import StreamReader, StreamWriter
from collections.abc import Iterable, Mapping
from random import choices as random_choices
from sys import stderr
from typing import IO

from PPpackage_utils.parse import (
    dump_bytes_chunked,
    dump_many,
    dump_one,
    load_bytes_chunked,
    load_one,
)
from PPpackage_utils.utils import SubmanagerCommand

from .utils import NodeData, SubmanagerCommandFailure, data_to_product


async def install_manager(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    manager: str,
    packages: Iterable[tuple[str, NodeData]],
) -> None:
    stderr.write(f"{manager}:\n")

    await dump_one(debug, writer, SubmanagerCommand.INSTALL)

    products = (data_to_product(package_name, data) for package_name, data in packages)

    await dump_many(debug, writer, products)

    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(f"{manager} failed to install packages.")

    for package_name, _ in sorted(packages, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")


def generate_machine_id(file: IO[bytes]):
    content_string = (
        "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
    )

    file.write(content_string.encode())


async def get_previous_installation(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    initial_installation: memoryview,
    previous_manager: str | None,
):
    if previous_manager is None:
        return initial_installation

    previous_reader, previous_writer = connections[previous_manager]

    await dump_one(debug, previous_writer, SubmanagerCommand.INSTALL_DOWNLOAD)

    installation = await load_bytes_chunked(debug, previous_reader)

    return installation


async def install(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    initial_installation: memoryview,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    previous_manager: str | None = None

    for generation in generations:
        for manager, packages in generation.items():
            reader, writer = connections[manager]

            if previous_manager != manager:
                installation = await get_previous_installation(
                    debug, connections, initial_installation, previous_manager
                )

                await dump_one(debug, writer, SubmanagerCommand.INSTALL_UPLOAD)
                await dump_bytes_chunked(debug, writer, installation)

            await install_manager(debug, reader, writer, manager, packages)

            previous_manager = manager

    installation = await get_previous_installation(
        debug, connections, initial_installation, previous_manager
    )

    return installation
