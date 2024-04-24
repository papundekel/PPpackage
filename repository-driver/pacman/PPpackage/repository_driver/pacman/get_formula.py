from collections.abc import AsyncIterable, MutableSequence

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import package_provides


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    provides = dict[str | tuple[str, str], MutableSequence[str]]()

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)

        for package in database.pkgcache:
            full_name = f"pacman-{package.name}-{package.version}"

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

            for provide in package_provides(package.provides):
                provides.setdefault(provide, []).append(full_name)

    for provide, packages in provides.items():
        variable_string = (
            provide if isinstance(provide, str) else f"{provide[0]}-{provide[1]}"
        )

        yield ImplicationRequirement(
            SimpleRequirement("noop", f"pacman-{variable_string}"),
            (
                XORRequirement(
                    [SimpleRequirement("noop", package) for package in packages]
                )
                if len(packages) > 1
                else SimpleRequirement("noop", packages[0])
            ),
        )
