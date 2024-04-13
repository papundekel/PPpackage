from typing import AsyncIterable

from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    NegatedRequirement,
    Requirement,
    SimpleRequirement,
)

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: ConanOptions,
) -> AsyncIterable[Requirement]:
    yield ImplicationRequirement(
        SimpleRequirement("noop", "conan-openssl-3.1.0"),
        SimpleRequirement("pacman", "sh"),
    )

    yield ImplicationRequirement(
        SimpleRequirement("noop", "conan-openssl-3.1.1"),
        SimpleRequirement("pacman", "sh"),
    )

    yield ImplicationRequirement(
        SimpleRequirement("noop", "conan-openssl-3.1.1"),
        NegatedRequirement(SimpleRequirement("noop", "conan-openssl-3.1.0")),
    )
