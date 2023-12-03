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
from pydantic import RootModel

from .utils import NodeData, data_to_product


async def install_manager(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    manager: str,
    packages: Iterable[tuple[str, NodeData]],
):
    stderr.write(f"{manager}:\n")
    for package_name, _ in sorted(packages, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")

    await dump_one(debug, writer, SubmanagerCommand.INSTALL)

    products = (data_to_product(package_name, data) for package_name, data in packages)

    await dump_many(debug, writer, products)

    await load_one(debug, reader, RootModel[None])


def generate_machine_id(file: IO[bytes]):
    content_string = (
        "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
    )

    file.write(content_string.encode())


async def get_last_installation(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    initial_installation: memoryview,
    last_manager: str | None,
):
    if last_manager is None:
        return initial_installation

    last_reader, last_writer = connections[last_manager]

    await dump_one(debug, last_writer, SubmanagerCommand.INSTALL_DOWNLOAD)

    installation = await load_bytes_chunked(debug, last_reader)

    return installation


async def install(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    initial_installation: memoryview,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    last_manager: str | None = None

    for generation in generations:
        for manager, packages in generation.items():
            reader, writer = connections[manager]

            if last_manager != manager:
                installation = await get_last_installation(
                    debug, connections, initial_installation, last_manager
                )

                await dump_one(debug, writer, SubmanagerCommand.INSTALL_UPLOAD)
                await dump_bytes_chunked(debug, writer, installation)

            await install_manager(debug, reader, writer, manager, packages)

            last_manager = manager

    installation = await get_last_installation(
        debug, connections, initial_installation, last_manager
    )

    return installation
