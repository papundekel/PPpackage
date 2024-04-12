from PPpackage.repository_driver.interface.exceptions import CommandException
from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from .schemes import DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    package: str,
) -> PackageDetail:
    if package.startswith("conan-openssl"):
        return PackageDetail(
            frozenset(),
            frozenset(["sh"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/openssl/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("conan-nameof"):
        return PackageDetail(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/pipe-rename/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
