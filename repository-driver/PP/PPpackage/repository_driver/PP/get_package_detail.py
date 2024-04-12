from PPpackage.repository_driver.interface.schemes import DetailPackageInfo

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    package: str,
) -> DetailPackageInfo:
    if package.startswith("PP-p1"):
        return DetailPackageInfo(frozenset(["p1"]), frozenset())
    elif package.startswith("PP-p2"):
        return DetailPackageInfo(frozenset(["p2"]), frozenset(["p1"]))
    elif package.startswith("PP-p3"):
        return DetailPackageInfo(frozenset(["p3"]), frozenset(["p2"]))
    else:
        return DetailPackageInfo(frozenset(), frozenset())
