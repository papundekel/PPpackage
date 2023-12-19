from collections.abc import Iterable, Mapping
from sys import stderr

from PPpackage_utils.parse import (
    ManagerAndName,
    dump_bytes_chunked,
    dump_one,
    load_bytes_chunked,
    load_one,
)
from PPpackage_utils.utils import SubmanagerCommand

from .utils import Connections, NodeData, data_to_product, load_success


async def install_patch(
    debug: bool,
    connections: Connections,
    manager: str,
    id: str,
    package_name: str,
    package_data: NodeData,
) -> None:
    stderr.write(f"{manager}: ")

    async with connections.connect(debug, manager, SubmanagerCommand.INSTALL_PATCH) as (
        reader,
        writer,
    ):
        await dump_one(debug, writer, id)
        await dump_one(debug, writer, data_to_product(package_name, package_data))

        await load_success(
            debug, reader, f"{manager} failed to install package {package_name}."
        )

        stderr.write(f"{package_name}\n")


async def install_get(
    debug: bool,
    connections: Connections,
    initial_installation: memoryview,
    previous_manager: str | None,
    ids: Mapping[str, str],
):
    if previous_manager is None:
        return initial_installation

    async with connections.connect(
        debug, previous_manager, SubmanagerCommand.INSTALL_GET
    ) as (previous_reader, previous_writer):
        await dump_one(debug, previous_writer, ids[previous_manager])

        installation = await load_bytes_chunked(debug, previous_reader)

        return installation


async def install_post(
    debug: bool,
    connections: Connections,
    manager: str,
    installation: memoryview,
):
    async with connections.connect(debug, manager, SubmanagerCommand.INSTALL_POST) as (
        reader,
        writer,
    ):
        await dump_bytes_chunked(debug, writer, installation)

        id = await load_one(debug, reader, str)

        return id


async def install_put(
    debug: bool,
    connections: Connections,
    manager: str,
    id: str,
    installation: memoryview,
):
    async with connections.connect(debug, manager, SubmanagerCommand.INSTALL_PUT) as (
        reader,
        writer,
    ):
        await dump_one(debug, writer, id)
        await dump_bytes_chunked(debug, writer, installation)

        await load_success(
            debug, reader, f"{manager} failed to update installation {id}."
        )


async def install_delete(
    debug: bool,
    connections: Connections,
    manager: str,
    id: str,
):
    async with connections.connect(
        debug, manager, SubmanagerCommand.INSTALL_DELETE
    ) as (
        reader,
        writer,
    ):
        await dump_one(debug, writer, id)

        await load_success(debug, reader, f"Failed to delete installation {id}.")


async def install(
    debug: bool,
    connections: Connections,
    initial_installation: memoryview,
    order: Iterable[tuple[ManagerAndName, NodeData]],
) -> memoryview:
    stderr.write(f"Installing packages...\n")

    previous_manager: str | None = None
    ids = dict[str, str]()

    for node, data in order:
        manager = node.manager

        if previous_manager != manager:
            installation = await install_get(
                debug, connections, initial_installation, previous_manager, ids
            )

            id = ids.get(manager)

            if id is None:
                id = await install_post(debug, connections, manager, installation)
                ids[manager] = id
            else:
                await install_put(debug, connections, manager, id, installation)
        else:
            id = ids[manager]

        await install_patch(debug, connections, manager, id, node.name, data)

        previous_manager = manager

    installation = await install_get(
        debug, connections, initial_installation, previous_manager, ids
    )

    for manager, id in ids.items():
        await install_delete(debug, connections, manager, id)

    return installation
