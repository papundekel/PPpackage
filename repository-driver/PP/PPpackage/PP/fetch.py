from collections.abc import AsyncIterable
from logging import getLogger
from pathlib import Path
from sys import stderr

from PPpackage.submanager.schemes import (
    Dependency,
    FetchRequest,
    Options,
    Package,
    ProductIDAndInfo,
)

from utils.utils import discard_async_iterable

from .settings import Settings

logger = getLogger(__name__)


async def empty_requirements():
    for _ in []:
        yield "", None


async def request_generators():
    yield "versions"


def print_directory(directory: Path):
    stderr.write("PP test:\n")
    for member in directory.iterdir():
        stderr.write(f"\t{member.name}")


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

    if generators_path is None:
        logger.debug("Need build context.")

        return FetchRequest(empty_requirements(), request_generators())

    await discard_async_iterable(dependencies)

    if installation_path is not None:
        print_directory(installation_path)

    print_directory(generators_path)

    logger.debug(f"Fetched {package.name} {package.version}.")

    return ProductIDAndInfo("id", None)
