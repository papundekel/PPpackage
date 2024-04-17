from PPpackage.repository_driver.interface.exceptions import CommandException
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
    if package.startswith("PP-p1"):
        return PackageDetail(
            frozenset(["p1"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("PP-p2"):
        return PackageDetail(
            frozenset(["p2"]),
            frozenset(["p1"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("PP-p3"):
        return PackageDetail(
            frozenset(["p3"]),
            frozenset(["p2"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
