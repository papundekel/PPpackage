from collections.abc import Iterable, Mapping
from typing import Any, AsyncIterable, TypeVar

from PPpackage_repository_driver.interface import load_interface_module
from PPpackage_repository_driver.schemes import (
    ResolutionLiteral,
    VariableToPackageVersionMapping,
)
from PPpackage_utils.validation import load_object

from .repository import Repository
from .schemes import LocalRepositoryConfig, RepositoryDriverConfig

RequirementType = TypeVar("RequirementType")


async def make_async_requirements(
    Requirement: type[RequirementType], requirements: Iterable[Any]
) -> AsyncIterable[RequirementType]:
    for requirement in requirements:
        yield load_object(Requirement, requirement)


class LocalRepository(Repository):
    def __init__(
        self,
        config: LocalRepositoryConfig,
        drivers: Mapping[str, RepositoryDriverConfig],
    ):
        driver_config = drivers[config.driver]

        self.interface = load_interface_module(driver_config.package)
        self.driver_parameters = driver_config.parameters
        self.repository_parameters = config.parameters

    async def translate_options(self, options: Any) -> Any:
        return self.interface.translate_options(
            self.driver_parameters, self.repository_parameters, options
        )

    def fetch_packages(
        self,
        translated_options: Any,
    ) -> AsyncIterable[list[ResolutionLiteral] | VariableToPackageVersionMapping]:
        return self.interface.fetch_packages(
            self.driver_parameters, self.repository_parameters, translated_options
        )
