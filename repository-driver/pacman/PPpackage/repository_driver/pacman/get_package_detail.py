from itertools import chain

from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, strip_version


async def get_package_detail(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    name, version = parse_package_name(full_package_name)

    database = state.handle.register_syncdb("database", 0)

    package = database.get_pkg(name)

    if package is None:
        return None

    if package.version != version:
        return None

    database.servers = repository_parameters.mirrorlist

    transaction = state.handle.init_transaction(
        downloadonly=True, nodeps=True, nodepversion=True
    )

    try:
        transaction.add_pkg(package)
        transaction.prepare()
        transaction.commit()
    finally:
        transaction.release()

    archive_path = (
        state.cache_directory_path / f"{name}-{version}-{package.arch}.pkg.tar.zst"
    )

    if not archive_path.exists():
        archive_path = (
            state.cache_directory_path / f"{name}-{version}-{package.arch}.pkg.tar.xz"
        )

    return PackageDetail(
        frozenset(
            chain(
                [f"pacman-{name}"],
                (f"pacman-{strip_version(provide)}" for provide in package.provides),
            )
        ),
        frozenset(
            f"pacman-{strip_version(dependency)}" for dependency in package.depends
        ),
        ArchiveProductDetail(archive_path, "pacman"),
    )
