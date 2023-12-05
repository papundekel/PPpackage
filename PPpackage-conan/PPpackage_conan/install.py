from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Mapping
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    TarFileInMemoryWrite,
    TarFileWithBytes,
    asubprocess_communicate,
    tar_append,
)

from .utils import Installation, get_cache_path, make_conan_environment


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
    data: Any,
    session_directory: Installation,
    cache_path: Path,
    products: AsyncIterable[Product],
):
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

        tar_append(session_directory.data, new_tar)

    session_directory.data = new_tar.data


async def install_upload(
    debug: bool,
    data: Any,
    session_directory: Installation,
    new_directory: memoryview,
):
    session_directory.data = new_directory


async def install_download(
    debug: bool,
    data: Any,
    session_directory: Installation,
) -> memoryview:
    return session_directory.data
