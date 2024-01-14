from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from PPpackage_submanager.schemes import Dependency, Options, Package, PackageIDAndInfo
from PPpackage_utils.utils import discard_async_iterable

from .settings import Settings


async def create_generators():
    yield "versions"


def print_directory(directory: Path):
    print("PP test:", file=stderr)
    for member in directory.iterdir():
        print(f"\t{member.name}", file=stderr)


async def fetch(
    settings: Settings,
    state: None,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> PackageIDAndInfo | AsyncIterable[str]:
    if generators_path is None:
        return create_generators()

    print(f"PP fetching package {package.name}", file=stderr)

    await discard_async_iterable(dependencies)

    if installation_path is not None:
        print_directory(installation_path)

    print_directory(generators_path)

    return PackageIDAndInfo("id", None)
