from typing import Any

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> ConanOptions:
    try:
        conan_options = options["conan"]

        if not isinstance(conan_options, dict):
            raise Exception

        return conan_options
    except:
        return {}
