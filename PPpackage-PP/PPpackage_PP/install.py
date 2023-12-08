from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

from PPpackage_PP.utils import Installation
from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    TarFileInMemoryWrite,
    create_tar_directory,
    create_tar_file,
    tar_append,
)


async def install(
    debug: bool,
    data: Any,
    session_directory: Installation,
    cache_path: Path,
    products: AsyncIterable[Product],
) -> bool:
    prefix = Path("PP")

    with TarFileInMemoryWrite() as new_tar:
        create_tar_directory(new_tar, prefix)

        async for product in products:
            product_path = prefix / product.name

            with create_tar_file(new_tar, product_path) as file:
                file.write(f"{product.version} {product.product_id}".encode())

        tar_append(session_directory.data, new_tar)

    session_directory.data = new_tar.data

    return True


async def install_upload(
    debug: bool,
    data: Any,
    session_directory: Installation,
    new_directory: memoryview,
):
    session_directory.data = new_directory


async def install_download(
    debug: bool,
    data: Any,
    session_directory: Installation,
) -> memoryview:
    return session_directory.data
