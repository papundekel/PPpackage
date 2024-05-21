from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import Requirement
from PPpackage.utils.async_ import Result

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    epoch_result: Result[str],
) -> AsyncIterable[list[Requirement]]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(repository_parameters.database_path / "epoch"))

        for alpm_package in state.database.pkgcache:
            name = alpm_package.name
            version = alpm_package.version

            for dependency in alpm_package.depends:
                yield [
                    Requirement("noop", f"pacman-{name}-{version}", False),
                    Requirement("pacman", dependency),
                ]

            for conflict in alpm_package.conflicts:
                yield [
                    Requirement("noop", f"pacman-{name}-{version}", False),
                    Requirement(
                        "pacman",
                        {"package": conflict, "exclude": f"{name}-{version}"},
                        False,
                    ),
                ]
