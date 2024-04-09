from collections.abc import AsyncIterable
from typing import Any

from PPpackage.repository_driver.interface.schemes import (
    Package,
    ResolutionLiteral,
    VariableToPackageVersionMapping,
)

from .schemes import DriverParameters, RepositoryParameters


async def fetch_packages(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
) -> AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping]:
    yield [ResolutionLiteral(False, "x-1.0.0"), ResolutionLiteral(True, "x-1.0.0")]
    yield VariableToPackageVersionMapping("x-1.0.0", Package("conan", "x"), "1.0.0")
