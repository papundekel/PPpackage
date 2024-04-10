from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import FetchPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[FetchPackageInfo]:
    yield FetchPackageInfo("pacman-bash-1.0.0", frozenset(["pacman-bash"]))
    yield FetchPackageInfo("pacman-zsh-1.0.0", frozenset(["pacman-zsh"]))
    yield FetchPackageInfo("pacman-coreutils-1.0.0", frozenset(["pacman-coreutils"]))
