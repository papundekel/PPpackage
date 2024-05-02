from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from PPpackage.utils.utils import Result

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def fetch_translator_data(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch_result: Result[str],
) -> AsyncIterable[TranslatorInfo]:
    epoch_result.set("0")

    yield TranslatorInfo("PP-p1", {"version": "1.0.0"})
    yield TranslatorInfo("PP-p2", {"version": "1.0.0"})
    yield TranslatorInfo("PP-p3", {"version": "1.0.0"})
