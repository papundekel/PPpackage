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
    if package.startswith("PP-p1"):
        return DetailPackageInfo(
            frozenset(["p1"]),
            frozenset(),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/drumkv1/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("PP-p2"):
        return DetailPackageInfo(
            frozenset(["p2"]),
            frozenset(["p1"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/adios2/download/",  # type: ignore
                "pacman",
            ),
        )
    elif package.startswith("PP-p3"):
        return DetailPackageInfo(
            frozenset(["p3"]),
            frozenset(["p2"]),
            ArchiveProductDetail(
                "https://archlinux.org/packages/extra/x86_64/aida-x-vst3/download/",  # type: ignore
                "pacman",
            ),
        )

    raise CommandException
