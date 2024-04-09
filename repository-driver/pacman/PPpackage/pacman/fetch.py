from asyncio import Lock, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable
from logging import getLogger
from pathlib import Path

from PPpackage.submanager.exceptions import CommandException
from PPpackage.submanager.schemes import (
    Dependency,
    FetchRequest,
    Options,
    Package,
    ProductIDAndInfo,
)
from pycman import run_action_with_args as pacman

from installer.pacman.PPpackage.installer.pacman.schemes import ProductInfo
from utils.utils import asubprocess_wait, discard_async_iterable, ensure_dir_exists

from .settings import Settings
from .utils import get_cache_paths

logger = getLogger(__name__)


def process_product_id(line: str):
    package_version_split = (
        line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
    )

    return f"{package_version_split[-2]}-{package_version_split[-1]}"


lock = Lock()


async def fetch(
    settings: Settings,
    state: None,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> ProductIDAndInfo | FetchRequest:
    logger.debug(f"Fetching {package.name} {package.version}...")

    database_path, cache_path = get_cache_paths(settings.cache_path)

    ensure_dir_exists(cache_path)

    await discard_async_iterable(dependencies)

    return_code = pacman(
        "sync",
        [
            "--dbpath",
            str(database_path),
            "--cachedir",
            str(cache_path),
            "--downloadonly",
            "--nodeps",
            "--nodeps",
            package.name,
        ],
    )

    if return_code != 0:
        raise CommandException(
            f"pacman failed to fetch {package.name} {package.version}."
        )

    process = await create_subprocess_exec(
        "pacman",
        "--dbpath",
        str(database_path),
        "--cachedir",
        str(cache_path),
        "--noconfirm",
        "--sync",
        "--nodeps",
        "--nodeps",
        "--print",
        package.name,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    assert process.stdout is not None

    line = (await process.stdout.readline()).decode().strip()

    await asubprocess_wait(process, CommandException)

    product_id = process_product_id(line)

    id_and_info = ProductIDAndInfo(
        product_id=product_id,
        product_info=ProductInfo(version=package.version, product_id=product_id),
    )

    logger.debug(f"Fetched {package.name} {package.version}.")

    return id_and_info
