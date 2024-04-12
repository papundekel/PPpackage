from collections.abc import AsyncIterable

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
    XORRequirement,
)

from .schemes import DriverParameters, RepositoryParameters


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[Requirement]:
    yield ImplicationRequirement(
        SimpleRequirement("noop", "pacman-sh"),
        XORRequirement(
            [
                SimpleRequirement("noop", "pacman-bash-1.0.0"),
                SimpleRequirement("noop", "pacman-zsh-1.0.0"),
            ]
        ),
    )
