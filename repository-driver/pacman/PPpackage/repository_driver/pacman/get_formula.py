from collections.abc import AsyncIterable

from pyalpm import Handle

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)
from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import strip_version


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    provides = dict[str, list[str]]()

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)

        for package in database.pkgcache:
            full_name = f"pacman-{package.name}-{package.version}-{package.arch}"

            if len(package.depends) != 0:
                yield ImplicationRequirement(
                    SimpleRequirement(
                        "noop",
                        full_name,
                    ),
                    ANDRequirement(
                        [
                            SimpleRequirement("pacman", dependency)
                            for dependency in package.depends
                        ]
                    ),
                )

            for provide in package.provides:
                provides.setdefault(strip_version(provide), []).append(full_name)

    for provide, packages in provides.items():
        yield ImplicationRequirement(
            SimpleRequirement("noop", f"pacman-{provide}"),
            (
                XORRequirement(
                    [SimpleRequirement("noop", package) for package in packages]
                )
                if len(packages) > 1
                else SimpleRequirement("noop", packages[0])
            ),
        )
