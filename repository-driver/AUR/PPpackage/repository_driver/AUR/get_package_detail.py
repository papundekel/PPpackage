from itertools import chain

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    MetaOnTopProductDetail,
    PackageDetail,
    SimpleRequirement,
)
from sqlitedict import SqliteDict

from .schemes import AURPackage, DriverParameters, RepositoryParameters
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

    with SqliteDict(
        repository_parameters.database_path / "database.sqlite",
        tablename="packages",
    ) as database:
        try:
            package: AURPackage = database[name]
        except KeyError:
            return None

    if package.Version != version:
        return None

    return PackageDetail(
        frozenset(
            chain(
                [f"pacman-{name}"],
                (f"pacman-{strip_version(provide)}" for provide in package.Provides),
            )
        ),
        frozenset(
            f"pacman-{strip_version(dependency)}" for dependency in package.Depends
        ),
        MetaOnTopProductDetail(
            ANDRequirement(
                [
                    SimpleRequirement("pacman", dependency)
                    for dependency in package.MakeDepends
                ]
            )
        ),
    )
