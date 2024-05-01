from collections.abc import Mapping
from typing import Any, AsyncIterable

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    PackageDetail,
    ProductInfo,
    Requirement,
    TranslatorInfo,
)

from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import validate_python

from .repository import RepositoryInterface
from .schemes import LocalRepositoryConfig, RepositoryDriverConfig


class LocalRepository(RepositoryInterface):
    def __init__(
        self,
        repository_config: LocalRepositoryConfig,
        drivers: Mapping[str, RepositoryDriverConfig],
    ):
        driver_config = drivers[repository_config.driver]

        interface = load_interface_module(Interface, driver_config.package)

        self.package = driver_config.package
        self.interface = interface
        self.driver_parameters = validate_python(
            interface.DriverParameters, driver_config.parameters
        )
        self.repository_parameters = validate_python(
            interface.RepositoryParameters, repository_config.parameters
        )

    def get_identifier(self) -> str:
        return self.package

    def get_url(self) -> None:
        return None

    async def get_epoch(self) -> str:
        return await self.interface.get_epoch(
            self.driver_parameters, self.repository_parameters
        )

    def fetch_translator_data(self, epoch: str) -> AsyncIterable[TranslatorInfo]:
        return self.interface.fetch_translator_data(
            self.driver_parameters, self.repository_parameters, epoch
        )

    async def translate_options(self, epoch: str, options: Any) -> Any:
        return await self.interface.translate_options(
            self.driver_parameters, self.repository_parameters, epoch, options
        )

    def get_formula(
        self, epoch: str, translated_options: Any
    ) -> AsyncIterable[Requirement]:
        return self.interface.get_formula(
            self.driver_parameters,
            self.repository_parameters,
            epoch,
            translated_options,
        )

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None:
        return await self.interface.get_package_detail(
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            package,
        )

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        dependency_product_infos: DependencyProductInfos,
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            package,
            dependency_product_infos,
        )
