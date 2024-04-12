from PPpackage.repository_driver.interface.schemes import DetailPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    package: str,
) -> DetailPackageInfo:
    if package.startswith("conan-openssl"):
        return DetailPackageInfo(frozenset(), frozenset(["sh"]))

    return DetailPackageInfo(frozenset(), frozenset())
