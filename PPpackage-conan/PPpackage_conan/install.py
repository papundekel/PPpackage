from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Mapping
from pathlib import Path
from shutil import copytree, rmtree

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import asubprocess_communicate, communicate_from_sub

from .utils import get_cache_path, make_conan_environment


async def install_product(
    debug: bool,
    environment: Mapping[str, str],
    destination_path: Path,
    product: Product,
) -> None:
    process = await create_subprocess_exec(
        "conan",
        "cache",
        "path",
        f"{product.name}/{product.version}:{product.product_id}",
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=DEVNULL,
        env=environment,
    )

    stdout = await asubprocess_communicate(process, "Error in `conan cache path`")

    product_path = stdout.decode("ascii").splitlines()[0]

    copytree(
        product_path, destination_path / product.name, symlinks=True, dirs_exist_ok=True
    )


async def install(
    debug: bool,
    cache_path: Path,
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
    products: AsyncIterable[Product],
) -> None:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    destination_path = destination_path / "conan"

    if destination_path.exists():
        rmtree(destination_path)

    async with TaskGroup() as group:
        async for product in products:
            group.create_task(
                install_product(debug, environment, destination_path, product)
            )

    with communicate_from_sub(pipe_from_sub_path), open(pipe_to_sub_path, "r"):
        pass
