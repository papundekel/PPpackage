from collections.abc import AsyncIterable, Iterable, MutableSequence
from typing import cast as type_cast

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)
from sqlitedict import SqliteDict

from .schemes import AURPackage, DriverParameters, RepositoryParameters
from .utils import package_provides


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    provides = dict[str | tuple[str, str], MutableSequence[str]]()

    with SqliteDict(
        repository_parameters.database_path / "database.sqlite",
        tablename="packages",
    ) as database:
        for package in type_cast(Iterable[AURPackage], database.values()):
            full_name = f"pacman-real-{package.Name}-{package.Version}"
            if len(package.Depends) != 0:
                yield ImplicationRequirement(
                    SimpleRequirement("noop", full_name),
                    ANDRequirement(
                        [
                            SimpleRequirement("pacman", dependency)
                            for dependency in package.Depends
                        ]
                    ),
                )

            for provide in package_provides(package.Provides):
                provides.setdefault(provide, []).append(full_name)

    for provide, packages in provides.items():
        variable_string = (
            provide if isinstance(provide, str) else f"{provide[0]}-{provide[1]}"
        )

        yield ImplicationRequirement(
            SimpleRequirement("noop", f"pacman-virtual-{variable_string}"),
            (
                XORRequirement(
                    [SimpleRequirement("noop", package) for package in packages]
                )
                if len(packages) > 1
                else SimpleRequirement("noop", packages[0])
            ),
        )
