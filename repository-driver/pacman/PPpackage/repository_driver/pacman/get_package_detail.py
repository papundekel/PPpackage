from itertools import chain

from pyalpm import Handle
from pydantic import AnyUrl

from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)
from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import strip_version


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
) -> PackageDetail:
    full_name = package[len("pacman-") :]
    alpm_name = full_name.rsplit("-", 3)[0]

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)

        alpm_package = database.get_pkg(alpm_name)

        return PackageDetail(
            frozenset(
                chain(
                    [alpm_name],
                    (strip_version(provide) for provide in alpm_package.provides),
                )
            ),
            frozenset(
                [strip_version(dependency) for dependency in alpm_package.depends]
            ),
            ArchiveProductDetail(
                AnyUrl(
                    f"https://archive.archlinux.org/packages/{alpm_name[0]}/{alpm_name}/{full_name}.pkg.tar.zst"
                ),
                "pacman",
            ),
        )
