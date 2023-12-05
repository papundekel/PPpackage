from asyncio import StreamReader, StreamWriter, TaskGroup, open_unix_connection
from collections.abc import Mapping, MutableMapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, TypedDict

from PPpackage_utils.io import close_writer
from PPpackage_utils.parse import Product, dump_one
from PPpackage_utils.utils import SubmanagerCommand


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any


def data_to_product(name: str, node_data: NodeData) -> Product:
    return Product(
        name=name, version=node_data["version"], product_id=node_data["product_id"]
    )


async def close_submanager(debug: bool, writer: StreamWriter):
    await dump_one(debug, writer, SubmanagerCommand.END)
    await close_writer(writer)


@asynccontextmanager
async def communicate_with_submanagers(
    debug: bool, connections: Mapping[str, tuple[StreamReader, StreamWriter]]
):
    try:
        yield
    finally:
        async with TaskGroup() as group:
            for _, writer in connections.values():
                group.create_task(close_submanager(debug, writer))


async def open_submanager(
    manager: str,
    submanager_socket_paths: Mapping[str, Path],
    connections: MutableMapping[str, tuple[StreamReader, StreamWriter]],
):
    connection = connections.get(manager)

    if connection is None:
        socket_path = submanager_socket_paths[manager]

        connection = await open_unix_connection(socket_path)

        connections[manager] = connection

    return connection
