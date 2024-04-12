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
    if package.startswith("pacman-bash"):
        return PackageDetail(
            frozenset(["bash", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/bash/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-zsh"):
        return PackageDetail(
            frozenset(["zsh", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/zsh/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-coreutils"):
        return PackageDetail(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/coreutils/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
