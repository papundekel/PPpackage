from collections.abc import Mapping
from typing import Any, AsyncIterable

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import FetchPackageInfo, Requirement

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

        self.interface = interface
        self.driver_parameters = load_object(
            interface.DriverParameters, driver_config.parameters
        )
        self.repository_parameters = load_object(
            interface.RepositoryParameters, repository_config.parameters
        )

    def fetch_packages(self) -> AsyncIterable[FetchPackageInfo]:
        return self.interface.fetch_packages(
            self.driver_parameters, self.repository_parameters
        )

    async def translate_options(self, options: Any) -> Any:
        return await self.interface.translate_options(
            self.driver_parameters, self.repository_parameters, options
        )

    def fetch_formula(self, translated_options: Any) -> AsyncIterable[Requirement]:
        return self.interface.fetch_formula(
            self.driver_parameters, self.repository_parameters, translated_options
        )
