from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[TranslatorInfo]:
    yield TranslatorInfo("PP-p1", "1.0.0")
    yield TranslatorInfo("PP-p2", "1.0.0")
    yield TranslatorInfo("PP-p3", "1.0.0")
