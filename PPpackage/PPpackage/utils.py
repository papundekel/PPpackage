from asyncio import StreamReader, StreamWriter, TaskGroup, open_unix_connection
from collections.abc import Mapping, MutableMapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, TypedDict

from PPpackage_utils.io import close_writer
from PPpackage_utils.parse import Product, dump_one, load_one
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


class SubmanagerCommandFailure(Exception):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class Connections:
    def __init__(self, submanager_socket_paths: Mapping[str, Path]):
        self._submanager_socket_paths = submanager_socket_paths
        self._connections: MutableMapping[str, tuple[StreamReader, StreamWriter]] = {}

    async def connect(self, manager: str, strict: bool = False):
        connection = self._connections.get(manager)

        if connection is not None:
            return connection

        if strict:
            raise KeyError()

        socket_path = self._submanager_socket_paths[manager]

        connection = await open_unix_connection(socket_path)

        self._connections[manager] = connection

        return connection

    def duplicate(self):
        return Connections(self._submanager_socket_paths)

    @asynccontextmanager
    async def communicate(self, debug: bool):
        try:
            yield
        finally:
            async with TaskGroup() as group:
                for _, writer in self._connections.values():
                    group.create_task(close_submanager(debug, writer))


async def load_success(debug: bool, reader: StreamReader, message: str):
    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(message)
