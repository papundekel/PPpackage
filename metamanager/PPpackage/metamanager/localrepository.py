from collections.abc import Mapping
from typing import Any, AsyncIterable

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    DetailPackageInfo,
    DiscoveryPackageInfo,
    Requirement,
)

from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_object

from .repository import Repository
from .schemes import LocalRepositoryConfig, RepositoryDriverConfig


class LocalRepository(Repository):
    def __init__(
        self,
        repository_config: LocalRepositoryConfig,
        drivers: Mapping[str, RepositoryDriverConfig],
    ):
        driver_config = drivers[repository_config.driver]

        interface = load_interface_module(Interface, driver_config.package)

        self.package = driver_config.package
        self.interface = interface
        self.driver_parameters = load_object(
            interface.DriverParameters, driver_config.parameters
        )
        self.repository_parameters = load_object(
            interface.RepositoryParameters, repository_config.parameters
        )

    def get_identifier(self) -> str:
        return self.package

    def discover_packages(self) -> AsyncIterable[DiscoveryPackageInfo]:
        return self.interface.discover_packages(
            self.driver_parameters, self.repository_parameters
        )

    async def translate_options(self, options: Any) -> Any:
        return await self.interface.translate_options(
            self.driver_parameters, self.repository_parameters, options
        )

    def get_formula(self, translated_options: Any) -> AsyncIterable[Requirement]:
        return self.interface.get_formula(
            self.driver_parameters, self.repository_parameters, translated_options
        )

    async def get_package_detail(self, package: str) -> DetailPackageInfo:
        return await self.interface.get_package_detail(
            self.driver_parameters, self.repository_parameters, package
        )
