from PPpackage.repository_driver.interface.exceptions import CommandException
from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: ConanOptions,
    package: str,
) -> PackageDetail:
    if package.startswith("conan-openssl"):
        return PackageDetail(
            frozenset(),
            frozenset(["sh"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("conan-nameof"):
        return PackageDetail(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
