from typing import Any

from PPpackage.utils.rwlock import read as rwlock_read

from .epoch import get as get_epoch
from .schemes import DriverParameters, Options, RepositoryParameters
from .state import State


async def translate_options(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> tuple[str, Options]:
    database_path = repository_parameters.database_path

    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch = get_epoch(database_path / "epoch")

    try:
        conan_options = Options.model_validate(options["conan"])
    except:
        conan_options = Options(settings={}, options={})

    return epoch, conan_options
