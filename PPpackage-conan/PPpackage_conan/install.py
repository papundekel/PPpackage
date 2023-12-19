from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping
from pathlib import Path

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    SubmanagerCommandFailure,
    TarFileInMemoryWrite,
    TarFileWithBytes,
    asubprocess_wait,
    tar_append,
)

from .utils import Data, get_cache_path, make_conan_environment


async def install_product(
    debug: bool,
    environment: Mapping[str, str],
    prefix: Path,
    tar: TarFileWithBytes,
    product: Product,
):
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

    assert process.stdout is not None

    output_bytes = await process.stdout.read()

    await asubprocess_wait(process, SubmanagerCommandFailure())

    product_path = output_bytes.decode().splitlines()[0]

    tar.add(product_path, str(prefix / product.name))


async def install_patch(
    debug: bool,
    data: Data,
    cache_path: Path,
    id: str,
    product: Product,
):
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    prefix = Path("conan")

    with TarFileInMemoryWrite() as new_tar:
        await install_product(debug, environment, prefix, new_tar, product)

        installation = data.installations.get(id)
        tar_append(installation, new_tar)

    data.installations.put(id, new_tar.data)


async def install_post(
    debug: bool,
    data: Data,
    new_directory: memoryview,
) -> str:
    return data.installations.add(new_directory)


async def install_put(
    debug: bool,
    data: Data,
    id: str,
    new_directory: memoryview,
) -> None:
    data.installations.put(id, new_directory)


async def install_get(
    debug: bool,
    data: Data,
    id: str,
) -> memoryview:
    return data.installations.get(id)


async def install_delete(
    debug: bool,
    data: Data,
    id: str,
) -> None:
    data.installations.remove(id)
