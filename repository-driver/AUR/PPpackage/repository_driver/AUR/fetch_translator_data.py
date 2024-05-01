from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
) -> AsyncIterable[TranslatorInfo]:
    yield TranslatorInfo("pacman-real-conan", {"version": "1.0.0-1-any"})
