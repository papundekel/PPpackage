from collections.abc import Set
from pathlib import Path

from PPpackage_utils.utils import Product


async def install(
    cache_path: Path,
    products: Set[Product],
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
) -> None:
    pass
