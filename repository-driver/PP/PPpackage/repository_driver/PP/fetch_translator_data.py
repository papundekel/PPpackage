from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
) -> AsyncIterable[TranslatorInfo]:
    yield TranslatorInfo("PP-p1", {"version": "1.0.0"})
    yield TranslatorInfo("PP-p2", {"version": "1.0.0"})
    yield TranslatorInfo("PP-p3", {"version": "1.0.0"})
