from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
)

from PPpackage.utils.utils import Result

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    epoch_result: Result[str],
) -> AsyncIterable[Requirement]:
    epoch_result.set("0")

    yield ImplicationRequirement(
        SimpleRequirement("noop", "PP-p2-1.0.0"),
        SimpleRequirement("noop", "PP-p1-1.0.0"),
    )

    yield ImplicationRequirement(
        SimpleRequirement("noop", "PP-p3-1.0.0"),
        SimpleRequirement("noop", "PP-p2-1.0.0"),
    )
