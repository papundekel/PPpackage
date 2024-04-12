from PPpackage.repository_driver.interface.schemes import DetailPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    package: str,
) -> DetailPackageInfo:
    if package.startswith("pacman-bash"):
        return DetailPackageInfo(frozenset(["bash", "sh"]), frozenset())
    elif package.startswith("pacman-zsh"):
        return DetailPackageInfo(frozenset(["zsh", "sh"]), frozenset())
    else:
        return DetailPackageInfo(frozenset(), frozenset())
