from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Any, AsyncIterable

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)

from PPpackage.utils.utils import Result, load_interface_module
from PPpackage.utils.validation import validate_python

from .repository import RepositoryInterface
from .schemes import LocalRepositoryConfig, RepositoryDriverConfig


class LocalRepository(RepositoryInterface):
    def __init__(
        self,
        package: str,
        interface: Interface,
        state: Any,
        driver_parameters: Any,
        repository_parameters: Any,
    ):
        self.package = package
        self.interface = interface
        self.state = state
        self.driver_parameters = driver_parameters
        self.repository_parameters = repository_parameters

    @staticmethod
    @asynccontextmanager
    async def create(
        repository_config: LocalRepositoryConfig,
        drivers: Mapping[str, RepositoryDriverConfig],
    ):
        driver_config = drivers[repository_config.driver]

        interface = load_interface_module(Interface, driver_config.package)

        package = driver_config.package
        driver_parameters = validate_python(
            interface.DriverParameters, driver_config.parameters
        )
        repository_parameters = validate_python(
            interface.RepositoryParameters, repository_config.parameters
        )

        async with interface.lifespan(
            driver_parameters, repository_parameters
        ) as state:
            yield LocalRepository(
                package, interface, state, driver_parameters, repository_parameters
            )

    def get_identifier(self) -> str:
        return self.package

    def get_url(self) -> None:
        return None

    async def get_epoch(self) -> str:
        return await self.interface.get_epoch(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
        )

    def fetch_translator_data(
        self, epoch_result: Result[str]
    ) -> AsyncIterable[TranslatorInfo]:
        return self.interface.fetch_translator_data(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            epoch_result,
        )

    async def translate_options(self, options: Any) -> tuple[str, Any]:
        return await self.interface.translate_options(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            options,
        )

    def get_formula(
        self, translated_options: Any, epoch_result: Result[str]
    ) -> AsyncIterable[Requirement]:
        return self.interface.get_formula(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            epoch_result,
        )

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None:
        return await self.interface.get_package_detail(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            package,
        )

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail:
        return await self.interface.get_build_context(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            package,
            runtime_product_infos,
        )

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_product_infos: ProductInfos,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            self.state,
            self.driver_parameters,
            self.repository_parameters,
            translated_options,
            package,
            build_product_infos,
            runtime_product_infos,
        )
