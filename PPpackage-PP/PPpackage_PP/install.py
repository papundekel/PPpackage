from pathlib import Path

from PPpackage_submanager.schemes import Product
from PPpackage_utils.tar import TarFileInMemoryAppend
from PPpackage_utils.tar import create_directory as create_tar_directory
from PPpackage_utils.tar import create_file as create_tar_file

from .database import User
from .utils import State


async def install_patch(
    debug: bool,
    state: State,
    user: User,
    cache_path: Path,
    id: str,
    product: Product,
):
    prefix = Path("PP")

    installation = state.installations.get(id)

    with TarFileInMemoryAppend(installation) as new_tar:
        create_tar_directory(new_tar, prefix)

        product_path = prefix / product.name

        with create_tar_file(new_tar, product_path) as file:
            file.write(f"{product.version} {product.product_id}".encode())

    state.installations.put(id, new_tar.data)


async def install_post(
    debug: bool,
    state: State,
    user: User,
    new_directory: memoryview,
) -> str:
    return state.installations.add(new_directory)


async def install_put(
    debug: bool,
    state: State,
    user: User,
    id: str,
    new_directory: memoryview,
) -> None:
    state.installations.put(id, new_directory)


async def install_get(
    debug: bool,
    state: State,
    user: User,
    id: str,
) -> memoryview:
    return state.installations.get(id)


async def install_delete(
    debug: bool,
    state: State,
    user: User,
    id: str,
) -> None:
    state.installations.remove(id)
