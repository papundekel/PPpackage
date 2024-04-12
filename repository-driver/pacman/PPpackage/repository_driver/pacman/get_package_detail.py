from PPpackage.repository_driver.interface.exceptions import CommandException
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
    if package.startswith("pacman-bash"):
        return DetailPackageInfo(
            frozenset(["bash", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/bash/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-zsh"):
        return DetailPackageInfo(
            frozenset(["zsh", "sh"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/zsh/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("pacman-coreutils"):
        return DetailPackageInfo(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/coreutils/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
