from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from PPpackage.utils.rwlock import read as rwlock_read
from PPpackage.utils.utils import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import package_provides


async def fetch_translator_data(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch_result: Result[str],
) -> AsyncIterable[TranslatorInfo]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(repository_parameters.database_path / "epoch"))

        database = state.handle.register_syncdb("database", 0)
        database.servers = repository_parameters.mirrorlist

        for package in database.pkgcache:
            yield TranslatorInfo(
                f"pacman-real-{package.name}",
                {"version": package.version},
            )

            for provide in package_provides(package.provides):
                match provide:
                    case library, version:
                        yield TranslatorInfo(
                            f"pacman-virtual-{library}", {"version": version}
                        )
                    case str():
                        yield TranslatorInfo(f"pacman-virtual-{provide}", {})
