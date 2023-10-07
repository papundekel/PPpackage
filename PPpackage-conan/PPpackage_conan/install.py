from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping, Set
from pathlib import Path
from shutil import copytree, rmtree

from PPpackage_utils.utils import Product, asubprocess_communicate, communicate_from_sub

from .utils import get_cache_path, make_conan_environment


async def install_product(
    environment: Mapping[str, str], destination_path: Path, product: Product
) -> None:
    process = await create_subprocess_exec(
        "conan",
        "cache",
        "path",
        f"{product.package}/{product.version}:{product.product_id}",
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
        env=environment,
    )

    stdout = await asubprocess_communicate(process, "Error in `conan cache path`")

    product_path = stdout.decode("ascii").splitlines()[0]

    copytree(
        product_path,
        destination_path / product.package,
        symlinks=True,
        dirs_exist_ok=True,
    )


async def install(
    cache_path: Path,
    products: Set[Product],
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
) -> None:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    destination_path = destination_path / "conan"

    if destination_path.exists():
        rmtree(destination_path)

    async with TaskGroup() as group:
        for product in products:
            group.create_task(install_product(environment, destination_path, product))

    with communicate_from_sub(pipe_from_sub_path), open(pipe_to_sub_path, "r"):
        pass