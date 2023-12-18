from asyncio import StreamReader, StreamWriter
from collections.abc import Iterable, Mapping, Sequence
from sys import stderr

from PPpackage_utils.parse import (
    dump_bytes_chunked,
    dump_many,
    dump_one,
    load_bytes_chunked,
    load_one,
)
from PPpackage_utils.utils import SubmanagerCommand

from .utils import Connections, NodeData, data_to_product, load_success


async def install_patch(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    manager: str,
    id: str,
    packages: Iterable[tuple[str, NodeData]],
) -> None:
    stderr.write(f"{manager}:\n")

    await dump_one(debug, writer, SubmanagerCommand.INSTALL_PATCH)

    await dump_one(debug, writer, id)

    products = (data_to_product(package_name, data) for package_name, data in packages)

    await dump_many(debug, writer, products)

    await load_success(debug, reader, f"{manager} failed to install packages.")

    for package_name, _ in sorted(packages, key=lambda p: p[0]):
        stderr.write(f"\t{package_name}\n")


async def install_get(
    debug: bool,
    connections: Connections,
    initial_installation: memoryview,
    previous_manager: str | None,
    ids: Mapping[str, str],
):
    if previous_manager is None:
        return initial_installation

    previous_reader, previous_writer = await connections.connect(previous_manager)

    await dump_one(debug, previous_writer, SubmanagerCommand.INSTALL_GET)
    await dump_one(debug, previous_writer, ids[previous_manager])

    installation = await load_bytes_chunked(debug, previous_reader)

    return installation


async def install_post(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    installation: memoryview,
):
    await dump_one(debug, writer, SubmanagerCommand.INSTALL_POST)
    await dump_bytes_chunked(debug, writer, installation)

    id = await load_one(debug, reader, str)

    return id


async def install_put(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    id: str,
    installation: memoryview,
):
    await dump_one(debug, writer, SubmanagerCommand.INSTALL_PUT)
    await dump_one(debug, writer, id)
    await dump_bytes_chunked(debug, writer, installation)

    await load_success(debug, reader, f"Failed to update installation {id}.")


async def install_delete(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    id: str,
):
    await dump_one(debug, writer, SubmanagerCommand.INSTALL_DELETE)
    await dump_one(debug, writer, id)

    await load_success(debug, reader, f"Failed to delete installation {id}.")


async def install(
    debug: bool,
    connections: Connections,
    initial_installation: memoryview,
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    previous_manager: str | None = None
    ids = dict[str, str]()

    for generation in generations:
        for manager, packages in generation.items():
            if len(packages) == 0:
                continue

            reader, writer = await connections.connect(manager)

            if previous_manager != manager:
                installation = await install_get(
                    debug, connections, initial_installation, previous_manager, ids
                )

                id = ids.get(manager)

                if id is None:
                    id = await install_post(debug, reader, writer, installation)
                    ids[manager] = id
                else:
                    await install_put(debug, reader, writer, id, installation)
            else:
                id = ids[manager]

            await install_patch(debug, reader, writer, manager, id, packages)

            previous_manager = manager

    installation = await install_get(
        debug, connections, initial_installation, previous_manager, ids
    )

    for manager, id in ids.items():
        reader, writer = await connections.connect(manager)

        await install_delete(debug, reader, writer, id)

    return installation
