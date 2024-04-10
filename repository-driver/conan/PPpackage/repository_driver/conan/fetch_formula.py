from collections.abc import AsyncIterable, Mapping
from typing import Any

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    NegatedRequirement,
    Requirement,
    SimpleRequirement,
)

from .schemes import DriverParameters, RepositoryParameters


async def fetch_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Mapping[str, Any],
) -> AsyncIterable[Requirement]:
    yield ImplicationRequirement(
        SimpleRequirement("noop", "conan-openssl-3.1.0"),
        SimpleRequirement("pacman", "sh"),
    )
