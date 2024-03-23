from pathlib import Path

from PPpackage_pacman_utils.install import pacman_install
from PPpackage_submanager.schemes import Product

from .settings import Settings
from .utils import get_cache_paths


async def install(
    settings: Settings,
    state: None,
    installation_path: Path,
    product: Product,
):
    _, cache_path = get_cache_paths(settings.cache_path)

    await pacman_install(
        settings.containerizer,
        settings.workdir_containerizer,
        settings.workdir_container,
        installation_path,
        cache_path
        / f"{product.name}-{product.version}-{product.product_id}.pkg.tar.zst",
    )
