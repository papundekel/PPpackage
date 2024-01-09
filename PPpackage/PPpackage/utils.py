from asyncio import StreamReader, StreamWriter, open_unix_connection
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, TypedDict

from PPpackage_utils.parse import Product, dump_one, load_one
from PPpackage_utils.pipe import close_writer
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

    @asynccontextmanager
    async def connect(self, debug: bool, manager: str, command: SubmanagerCommand):
        socket_path = self._submanager_socket_paths[manager]

        reader, writer = await open_unix_connection(socket_path)
        await dump_one(debug, writer, command)

        try:
            yield reader, writer
        finally:
            await close_submanager(debug, writer)


async def load_success(debug: bool, reader: StreamReader, message: str):
    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(message)
