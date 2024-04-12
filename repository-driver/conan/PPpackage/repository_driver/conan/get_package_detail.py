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
    if package.startswith("conan-openssl"):
        return DetailPackageInfo(
            frozenset(),
            frozenset(["sh"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/core/x86_64/openssl/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("conan-nameof"):
        return DetailPackageInfo(
            frozenset(),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/pipe-rename/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
