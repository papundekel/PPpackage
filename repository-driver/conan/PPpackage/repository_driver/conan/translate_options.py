from typing import Any

from .schemes import DriverParameters, Options, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
    options: Any,
) -> Options:
    try:
        conan_options = options["conan"]

        return Options.model_validate(conan_options)
    except:
        return Options(settings={}, options={})
