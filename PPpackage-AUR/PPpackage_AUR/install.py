from pathlib import Path

from PPpackage_submanager.schemes import Product
from PPpackage_utils.utils import ensure_dir_exists

from .settings import Settings


async def install(
    settings: Settings,
    state: None,
    installation_path: Path,
    product: Product,
):
    prefix = Path("AUR")

    products_path = installation_path / prefix

    ensure_dir_exists(products_path)

    product_path = products_path / product.name

    with product_path.open("w") as file:
        file.write(f"{product.version} {product.product_id}\n")
