from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import Product


async def install(
    debug: bool,
    data: Any,
    session_data: Any,
    cache_path: Path,
    products: AsyncIterable[Product],
):
    pass


async def install_upload(
    debug: bool,
    data: Any,
    session_data: Any,
    new_directory: memoryview,
):
    pass


async def install_download(
    debug: bool,
    data: Any,
    session_data: Any,
) -> memoryview:
    return memoryview(bytes())
