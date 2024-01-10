from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping
from pathlib import Path
from shutil import copytree

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Product
from PPpackage_utils.utils import asubprocess_wait

from .settings import Settings
from .utils import State, get_cache_path, make_conan_environment


async def install_product(
    debug: bool,
    environment: Mapping[str, str],
    installation_path: Path,
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

    await asubprocess_wait(process, CommandException())

    product_cache_path = output_bytes.decode().splitlines()[0]

    product_installation_path = installation_path / product.name

    copytree(product_cache_path, product_installation_path)


async def install(
    settings: Settings,
    state: State,
    installation_path: Path,
    product: Product,
):
    cache_path = get_cache_path(settings.cache_path)

    environment = make_conan_environment(cache_path)

    prefix = Path("conan")

    await install_product(
        settings.debug, environment, installation_path / prefix, product
    )
