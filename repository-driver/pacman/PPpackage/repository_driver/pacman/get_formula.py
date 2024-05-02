from collections.abc import AsyncIterable, MutableSequence

from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)

from PPpackage.utils.rwlock import read as rwlock_read
from PPpackage.utils.utils import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import package_provides


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    epoch_result: Result[str],
) -> AsyncIterable[Requirement]:
    provides = dict[str | tuple[str, str], MutableSequence[str]]()

    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(repository_parameters.database_path / "epoch"))

        database = state.handle.register_syncdb("database", 0)

        for package in database.pkgcache:
            full_name = f"pacman-real-{package.name}-{package.version}"
            if len(package.depends) != 0:
                yield ImplicationRequirement(
                    SimpleRequirement("noop", full_name),
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
            SimpleRequirement("noop", f"pacman-virtual-{variable_string}"),
            (
                XORRequirement(
                    [SimpleRequirement("noop", package) for package in packages]
                )
                if len(packages) > 1
                else SimpleRequirement("noop", packages[0])
            ),
        )
