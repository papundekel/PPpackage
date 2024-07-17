from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterable

from PPpackage.repository_driver.interface.interface import Interface
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    BuildContextInfo,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)
from PPpackage.utils.async_ import Result

from PPpackage.metamanager.schemes import RepositoryConfig, RepositoryDriverConfig
from PPpackage.utils.json.validate import validate_python
from PPpackage.utils.python import load_interface_module

from .interface import RepositoryInterface


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
        repository_config: RepositoryConfig,
        drivers: Mapping[str, RepositoryDriverConfig],
        data_path: Path,
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
            driver_parameters, repository_parameters, data_path
        ) as state:
            yield LocalRepository(
                package, interface, state, driver_parameters, repository_parameters
            )

    async def get_epoch(self) -> str:
        return await self.interface.get_epoch(self.state)

    def fetch_translator_data(
        self, epoch_result: Result[str]
    ) -> AsyncIterable[TranslatorInfo]:
        return self.interface.fetch_translator_data(self.state, epoch_result)

    async def translate_options(self, options: Any) -> tuple[str, Any]:
        return await self.interface.translate_options(self.state, options)

    def get_formula(
        self, translated_options: Any, epoch_result: Result[str]
    ) -> AsyncIterable[list[Requirement]]:
        return self.interface.get_formula(self.state, translated_options, epoch_result)

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None:
        return await self.interface.get_package_detail(
            self.state, translated_options, package
        )

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail:
        return await self.interface.get_build_context(
            self.state, translated_options, package, runtime_product_infos
        )

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_context_info: BuildContextInfo,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            self.state,
            translated_options,
            package,
            build_context_info,
            runtime_product_infos,
        )
