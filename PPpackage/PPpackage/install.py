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
)
from PPpackage_utils.utils import Phase

from .utils import NodeData, data_to_product


async def install_manager(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    manager: str,
    generation: Iterable[tuple[str, NodeData]],
    old_installation: memoryview,
) -> memoryview:
    stderr.write(f"{manager}:\n")
    for package_name, _ in sorted(generation, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")

    reader, writer = connections[manager]

    await dump_one(debug, writer, Phase.INSTALL)

    await dump_bytes_chunked(debug, writer, old_installation)

    products = (
        data_to_product(package_name, data) for package_name, data in generation
    )

    await dump_many(debug, writer, products)

    new_installation = await load_bytes_chunked(debug, reader)

    return new_installation


def generate_machine_id(file: IO[bytes]):
    content_string = (
        "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
    )

    file.write(content_string.encode())


async def install(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    installation: memoryview,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    for manager_to_generation in generations:
        for manager, generation in manager_to_generation.items():
            installation = await install_manager(
                debug, connections, manager, generation, installation
            )

    return installation
