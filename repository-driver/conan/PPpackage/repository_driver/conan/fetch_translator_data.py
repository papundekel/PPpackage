from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .schemes import DriverParameters, RepositoryParameters


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[TranslatorInfo]:
    yield TranslatorInfo("conan-openssl", "3.1.0")
    yield TranslatorInfo("conan-openssl", "3.1.1")
    yield TranslatorInfo("conan-nameof", "0.10.1")
