from collections.abc import AsyncIterable

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
    translated_options: None,
) -> AsyncIterable[Requirement]:
    yield ImplicationRequirement(
        SimpleRequirement("noop", "pacman-y-1.0.0"),
        SimpleRequirement("pacman", "x"),
    )
    yield ImplicationRequirement(
        SimpleRequirement("noop", "pacman-x-1.0.1"),
        NegatedRequirement(SimpleRequirement("noop", "pacman-x-1.0.0")),
    )
