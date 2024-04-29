from typing import Any

from PPpackage.utils.validation import load_object

from .schemes import DriverParameters, Options, RepositoryParameters


async def translate_options(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    options: Any,
) -> Options:
    try:
        conan_options = options["conan"]

        return load_object(Options, conan_options)
    except:
        return Options(settings={}, options={})
