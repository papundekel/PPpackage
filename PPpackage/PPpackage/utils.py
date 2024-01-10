from typing import Any, TypedDict

from PPpackage_submanager.schemes import Product
from PPpackage_utils.stream import Reader


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any


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
