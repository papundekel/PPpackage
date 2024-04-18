from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
)
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)
        database.servers = repository_parameters.mirrorlist

        for package in database.pkgcache:
            if len(package.depends) != 0:
                yield ImplicationRequirement(
                    SimpleRequirement("noop", f"pacman-{package.name}"),
                    ANDRequirement(
                        [
                            SimpleRequirement("pacman", dependency)
                            for dependency in package.depends
                        ]
                    ),
                )
