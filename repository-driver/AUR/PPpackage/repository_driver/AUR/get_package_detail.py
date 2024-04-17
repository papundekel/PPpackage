from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
) -> PackageDetail:
    return PackageDetail(
        frozenset(),
        frozenset(),
        ArchiveProductDetail(
            "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
            "pacman",
        ),
    )
