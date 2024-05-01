from itertools import chain
from pathlib import Path
from tempfile import mkdtemp

from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import PREFIX, parse_package_name, strip_version


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    name, version = parse_package_name(full_package_name)

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        cachedir_path = Path(mkdtemp())
        handle.add_cachedir(str(cachedir_path))

        database = handle.register_syncdb("database", 0)

        alpm_package = database.get_pkg(name)

        if alpm_package is None:
            return None

        if alpm_package.version != version:
            return None

        database.servers = repository_parameters.mirrorlist

        transaction = handle.init_transaction(
            downloadonly=True, nodeps=True, nodepversion=True
        )

        try:
            transaction.add_pkg(alpm_package)
            transaction.prepare()
            transaction.commit()
        finally:
            transaction.release()

        archive_path = next(cachedir_path.iterdir())

        return PackageDetail(
            frozenset(
                chain(
                    [f"pacman-{name}"],
                    (
                        f"pacman-{strip_version(provide)}"
                        for provide in alpm_package.provides
                    ),
                )
            ),
            frozenset(
                f"pacman-{strip_version(dependency)}"
                for dependency in alpm_package.depends
            ),
            ArchiveProductDetail(archive_path, "pacman"),
        )
