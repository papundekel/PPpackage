from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

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
    session_data: None,
    cache_path: Path,
    old_directory: memoryview,
    products: AsyncIterable[Product],
) -> memoryview:
    prefix = Path("PP")

    with TarFileInMemoryWrite() as new_tar:
        create_tar_directory(new_tar, prefix)

        async for product in products:
            product_path = prefix / product.name

            with create_tar_file(new_tar, product_path) as file:
                file.write(f"{product.version} {product.product_id}".encode())

        tar_append(old_directory, new_tar)

    return new_tar.data
