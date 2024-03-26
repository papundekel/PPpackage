from pathlib import Path

from PPpackage_pacman_utils.install import pacman_install
from PPpackage_submanager.schemes import Product

from .lifespan import State
from .settings import Settings
from .utils import make_product_key


async def install(
    settings: Settings,
    state: State,
    installation_path: Path,
    product: Product,
):
    product_key = make_product_key(product.name, product.version, product.product_id)

    product_path = state.product_paths[product_key]

    await pacman_install(
        settings.containerizer,
        settings.workdir,
        installation_path,
        product_path,
    )
