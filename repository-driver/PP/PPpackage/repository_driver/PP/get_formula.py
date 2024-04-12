from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
)

from .schemes import DriverParameters, RepositoryParameters


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    yield ImplicationRequirement(
        SimpleRequirement("noop", "PP-p2-1.0.0"),
        SimpleRequirement("noop", "PP-p1-1.0.0"),
    )

    yield ImplicationRequirement(
        SimpleRequirement("noop", "PP-p3-1.0.0"),
        SimpleRequirement("noop", "PP-p2-1.0.0"),
    )
