from pathlib import Path

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    TarFileInMemoryAppend,
    create_tar_directory,
    create_tar_file,
)

from .utils import Data


async def install_patch(
    debug: bool,
    data: Data,
    cache_path: Path,
    id: str,
    product: Product,
):
    prefix = Path("PP")

    installation = data.installations.get(id)

    with TarFileInMemoryAppend(installation) as new_tar:
        create_tar_directory(new_tar, prefix)

        product_path = prefix / product.name

        with create_tar_file(new_tar, product_path) as file:
            file.write(f"{product.version} {product.product_id}".encode())

    data.installations.put(id, new_tar.data)


async def install_post(
    debug: bool,
    data: Data,
    new_directory: memoryview,
) -> str:
    return data.installations.add(new_directory)


async def install_put(
    debug: bool,
    data: Data,
    id: str,
    new_directory: memoryview,
) -> None:
    data.installations.put(id, new_directory)


async def install_get(
    debug: bool,
    data: Data,
    id: str,
) -> memoryview:
    return data.installations.get(id)


async def install_delete(
    debug: bool,
    data: Data,
    id: str,
) -> None:
    data.installations.remove(id)
