from httpx import Response
from PPpackage_submanager.schemes import Product
from PPpackage_utils.http_stream import AsyncChunkReader
from PPpackage_utils.stream import Reader

from .schemes import NodeData


def data_to_product(name: str, node_data: NodeData) -> Product:
    return Product(
        name=name, version=node_data["version"], product_id=node_data["product_id"]
    )


class SubmanagerCommandFailure(Exception):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


async def load_success(reader: Reader, message: str):
    success = await reader.load_one(bool)

    if not success:
        raise SubmanagerCommandFailure(message)


def HTTPResponseReader(response: Response):
    return AsyncChunkReader(memoryview(chunk) async for chunk in response.aiter_raw())
