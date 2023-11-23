from io import BytesIO
from pathlib import Path
from tarfile import DIRTYPE, TarInfo
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


def create_tar_directory(tar, path: Path):
    info = TarInfo(name=str(path))
    info.mode = 0o755
    info.type = DIRTYPE

    tar.addfile(info)


def create_tar_file(tar, path: Path, data: bytes):
    with BytesIO(data) as io:
        info = TarInfo(name=str(path))
        info.size = len(data)

        tar.addfile(info, io)
