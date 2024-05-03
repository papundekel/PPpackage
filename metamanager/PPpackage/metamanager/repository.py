from collections.abc import AsyncIterable
from typing import Any, Protocol

from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)
from pydantic import AnyUrl
from sqlitedict import SqliteDict

from PPpackage.utils.utils import Result
from PPpackage.utils.validation import dump_json

from .exceptions import EpochException
from .schemes import RepositoryConfig


class RepositoryInterface(Protocol):
    def get_identifier(self) -> str: ...

    def get_url(self) -> AnyUrl | None: ...

    async def get_epoch(self) -> str: ...

    def fetch_translator_data(
        self, epoch_result: Result[str]
    ) -> AsyncIterable[TranslatorInfo]: ...

    async def translate_options(self, options: Any) -> tuple[str, Any]: ...

    def get_formula(
        self, translated_options: Any, epoch_result: Result[str]
    ) -> AsyncIterable[Requirement]: ...

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None: ...

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail: ...

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_product_infos: ProductInfos,
        runtime_product_infos: ProductInfos,
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
        self.config.translator_data_cache_path.parent.mkdir(parents=True, exist_ok=True)

        with SqliteDict(
            self.config.translator_data_cache_path
        ) as translator_data_cache:
            cache_key = self.epoch

            try:
                translator_data = translator_data_cache[cache_key]
            except KeyError:
                translator_data = []

                epoch_result = Result[str]()

                async for info in self.interface.fetch_translator_data(epoch_result):
                    yield info
                    translator_data.append(info)

                if epoch_result.get() != self.epoch:
                    raise EpochException()

                translator_data_cache[cache_key] = translator_data
                translator_data_cache.commit()
            else:
                for requirement in translator_data:
                    yield requirement

    async def translate_options(self, options: Any) -> None:
        epoch, translated_options = await self.interface.translate_options(options)

        if epoch != self.epoch:
            raise EpochException()

        self.translated_options = translated_options

    async def get_formula(self) -> AsyncIterable[Requirement]:
        self.config.formula_cache_path.parent.mkdir(parents=True, exist_ok=True)

        with SqliteDict(self.config.formula_cache_path) as formula_cache:
            serialized_translated_options = dump_json(self.translated_options)
            cache_key = f"{self.epoch}-{serialized_translated_options}"

            try:
                formula = formula_cache[cache_key]
            except KeyError:
                formula = []

                epoch_result = Result[str]()

                async for requirement in self.interface.get_formula(
                    self.translated_options, epoch_result
                ):
                    yield requirement
                    formula.append(requirement)

                if epoch_result.get() != self.epoch:
                    raise EpochException()

                formula_cache[cache_key] = formula
                formula_cache.commit()
            else:
                for requirement in formula:
                    yield requirement

    async def get_package_detail(self, package: str) -> PackageDetail | None:
        return await self.interface.get_package_detail(self.translated_options, package)

    async def get_build_context(
        self,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail:
        return await self.interface.get_build_context(
            self.translated_options, package, runtime_product_infos
        )

    async def compute_product_info(
        self,
        package: str,
        build_product_infos: ProductInfos,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            self.translated_options, package, build_product_infos, runtime_product_infos
        )
