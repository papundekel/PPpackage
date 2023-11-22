from collections.abc import AsyncIterable
from pathlib import Path

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import communicate_from_sub


async def install(
    debug: bool,
    cache_path: Path,
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
    products: AsyncIterable[Product],
) -> None:
    products_path = destination_path / "PP"

    products_path.mkdir(exist_ok=True)

    async for product in products:
        product_path = products_path / product.name
        product_path.write_text(f"{product.version} {product.product_id}")

    with communicate_from_sub(pipe_from_sub_path), open(pipe_to_sub_path, "r"):
        pass
