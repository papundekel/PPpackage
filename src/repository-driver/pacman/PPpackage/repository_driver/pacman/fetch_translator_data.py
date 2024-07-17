from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from PPpackage.utils.async_ import Result

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import package_provides


async def fetch_translator_data(
    state: State, epoch_result: Result[str]
) -> AsyncIterable[TranslatorInfo]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(state.database_path / "epoch"))

        for package in state.database.pkgcache:
            yield TranslatorInfo(f"pacman-{package.name}", {"version": package.version})

            provider = f"{package.name}-{package.version}"

            for provide in package_provides(package.provides):
                match provide:
                    case provide_name, version:
                        yield TranslatorInfo(
                            f"pacman-{provide_name}",
                            {"provider": provider, "version": version},
                        )
                    case provide_name:
                        yield TranslatorInfo(
                            f"pacman-{provide_name}", {"provider": provider}
                        )
