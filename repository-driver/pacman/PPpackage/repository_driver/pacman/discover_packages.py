from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import DiscoveryPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def discover_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[DiscoveryPackageInfo]:
    yield DiscoveryPackageInfo("pacman-bash-1.0.0", frozenset(["pacman-bash"]))
    yield DiscoveryPackageInfo("pacman-zsh-1.0.0", frozenset(["pacman-zsh"]))
    yield DiscoveryPackageInfo(
        "pacman-coreutils-1.0.0", frozenset(["pacman-coreutils"])
    )
