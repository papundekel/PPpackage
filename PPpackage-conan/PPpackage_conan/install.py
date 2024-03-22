from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping
from pathlib import Path
from shutil import copytree

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Product
from PPpackage_utils.utils import asubprocess_wait

from .lifespan import State
from .settings import Settings
from .utils import make_conan_environment


async def install_product(
    debug: bool,
    environment: Mapping[str, str],
    installation_path: Path,
    product: Product,
):
    product_installation_path = installation_path / product.name

    if product_installation_path.exists():
        return

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

    copytree(product_cache_path, product_installation_path)


async def install(
    settings: Settings,
    state: State,
    installation_path: Path,
    product: Product,
):
    environment = make_conan_environment(settings.cache_path)

    prefix = Path("conan")

    await install_product(
        settings.debug, environment, installation_path / prefix, product
    )
