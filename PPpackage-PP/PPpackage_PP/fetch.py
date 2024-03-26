from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from PPpackage_submanager.schemes import (
    Dependency,
    FetchRequest,
    Options,
    Package,
    ProductIDAndInfo,
)
from PPpackage_utils.utils import discard_async_iterable

from .settings import Settings


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
    if generators_path is None:
        return FetchRequest(empty_requirements(), request_generators())

    await discard_async_iterable(dependencies)

    if installation_path is not None:
        print_directory(installation_path)

    print_directory(generators_path)

    return ProductIDAndInfo("id", None)
