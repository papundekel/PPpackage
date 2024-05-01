from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    PackageDetail,
    ProductInfo,
    Requirement,
    TranslatorInfo,
)
from pydantic import AnyUrl
from sqlitedict import SqliteDict

from PPpackage.utils.validation import dump_json

from .schemes import RepositoryConfig


class RepositoryInterface(Protocol):
    def get_identifier(self) -> str: ...

    def get_url(self) -> AnyUrl | None: ...

    async def get_epoch(self) -> str: ...

    def fetch_translator_data(self, epoch: str) -> AsyncIterable[TranslatorInfo]: ...

    async def translate_options(self, epoch: str, options: Any) -> Any: ...

    def get_formula(
        self, epoch: str, translated_options: Any
    ) -> AsyncIterable[Requirement]: ...

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None: ...

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        dependency_product_infos: DependencyProductInfos,
    ) -> ProductInfo: ...


class Repository:
    def __init__(
        self, config: RepositoryConfig, interface: RepositoryInterface, epoch: str
    ):
        self.config = config
        self.interface = interface
        self.epoch = epoch

    @staticmethod
    async def create(config: RepositoryConfig, interface: RepositoryInterface):
        epoch = await interface.get_epoch()
        return Repository(config, interface, epoch)

    def get_identifier(self) -> str:
        return self.interface.get_identifier()

    def get_url(self) -> AnyUrl | None:
        return self.interface.get_url()

    async def fetch_translator_data(self) -> AsyncIterable[TranslatorInfo]:
        with SqliteDict(
            self.config.translator_data_cache_path
        ) as translator_data_cache:
            cache_key = self.epoch

            try:
                translator_data = translator_data_cache[cache_key]
            except KeyError:
                translator_data = []

                async for info in self.interface.fetch_translator_data(self.epoch):
                    yield info
                    translator_data.append(info)

                translator_data_cache[cache_key] = translator_data
                translator_data_cache.commit()
            else:
                for requirement in translator_data:
                    yield requirement

    async def translate_options(self, options: Any) -> None:
        self.translated_options = await self.interface.translate_options(
            self.epoch, options
        )

    async def get_formula(self) -> AsyncIterable[Requirement]:
        with SqliteDict(self.config.formula_cache_path) as formula_cache:
            serialized_translated_options = dump_json(self.translated_options)
            cache_key = f"{self.epoch}-{serialized_translated_options}"

            try:
                formula = formula_cache[cache_key]
            except KeyError:
                formula = []

                async for requirement in self.interface.get_formula(
                    self.epoch, self.translated_options
                ):
                    yield requirement
                    formula.append(requirement)

                formula_cache[cache_key] = formula
                formula_cache.commit()
            else:
                for requirement in formula:
                    yield requirement

    async def get_package_detail(self, package: str) -> PackageDetail | None:
        return await self.interface.get_package_detail(self.translated_options, package)

    async def compute_product_info(
        self, package: str, dependency_product_infos: DependencyProductInfos
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            self.translated_options, package, dependency_product_infos
        )
