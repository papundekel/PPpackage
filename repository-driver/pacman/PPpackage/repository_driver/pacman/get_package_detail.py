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
    if package.startswith("pacman-bash"):
        return PackageDetail(
            frozenset(["bash", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-zsh"):
        return PackageDetail(
            frozenset(["zsh", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-coreutils"):
        return PackageDetail(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/any/iana-etc/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException(f"Package {package} not found")
