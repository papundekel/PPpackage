from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    DetailPackageInfo,
)

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    package: str,
) -> DetailPackageInfo:
    return DetailPackageInfo(
        frozenset(),
        frozenset(),
        ArchiveProductDetail(
            "https://archlinux.org/packages/extra/x86_64/percona-server/download/",  # type: ignore
            "pacman",
        ),
    )
