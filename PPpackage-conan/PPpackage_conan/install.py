from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Mapping
from pathlib import Path

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    TarFileInMemoryWrite,
    TarFileWithBytes,
    asubprocess_communicate,
    tar_append,
)

from .utils import get_cache_path, make_conan_environment


async def install_product(
    debug: bool,
    environment: Mapping[str, str],
    prefix: Path,
    tar: TarFileWithBytes,
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

    tar.add(product_path, str(prefix / product.name))


async def install(
    debug: bool,
    cache_path: Path,
    runner_path: Path,
    runner_workdir_path: Path,
    old_directory: memoryview,
    products: AsyncIterable[Product],
) -> memoryview:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    prefix = Path("conan")

    with TarFileInMemoryWrite() as new_tar:
        async with TaskGroup() as group:
            async for product in products:
                group.create_task(
                    install_product(
                        debug,
                        environment,
                        prefix,
                        new_tar,
                        product,
                    )
                )

        tar_append(old_directory, new_tar)

    return new_tar.data
