from typing import Any, TypedDict

from PPpackage_utils.parse import Product


class NodeData(TypedDict):
    version: str
    product_id: str
    product_info: Any


def data_to_product(name: str, node_data: NodeData) -> Product:
    return Product(
        name=name, version=node_data["version"], product_id=node_data["product_id"]
    )
