from collections.abc import AsyncGenerator, AsyncIterable, Iterable, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

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
from sqlitedict import SqliteDict

from PPpackage.metamanager.exceptions import EpochException
from PPpackage.metamanager.schemes import RepositoryConfig, RepositoryDriverConfig
from PPpackage.utils.json.dump import dump_json

from .interface import RepositoryInterface
from .local import LocalRepository


class Repository:
    def __init__(
        self,
        config: RepositoryConfig,
        interface: RepositoryInterface,
        epoch: str,
        data_path: Path,
        index: int,
    ):
        self.translator_data_cache_path = (
            config.translator_data_cache_path
            if config.translator_data_cache_path is not None
            else data_path / "cache" / "translator-data" / str(index)
        )

        self.formula_cache_path = (
            config.formula_cache_path
            if config.formula_cache_path is not None
            else data_path / "cache" / "formula" / str(index)
        )

        self.interface = interface
        self.epoch = epoch

    @staticmethod
    async def create(
        config: RepositoryConfig,
        interface: RepositoryInterface,
        data_path: Path,
        index: int,
    ):
        epoch = await interface.get_epoch()
        return Repository(config, interface, epoch, data_path, index)

    async def fetch_translator_data(self) -> AsyncIterable[TranslatorInfo]:
        self.translator_data_cache_path.parent.mkdir(parents=True, exist_ok=True)

        with SqliteDict(self.translator_data_cache_path) as translator_data_cache:
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

    async def translate_options(self, options: Any) -> Any:
        epoch, translated_options = await self.interface.translate_options(options)

        if epoch != self.epoch:
            raise EpochException()

        return translated_options

    async def get_formula(
        self, translated_options: Any
    ) -> AsyncIterable[list[Requirement]]:
        self.formula_cache_path.parent.mkdir(parents=True, exist_ok=True)

        with SqliteDict(self.formula_cache_path) as formula_cache:
            serialized_translated_options = dump_json(translated_options)
            cache_key = f"{self.epoch}-{serialized_translated_options}"

            try:
                formula = formula_cache[cache_key]
            except KeyError:
                formula = []

                epoch_result = Result[str]()

                async for requirement in self.interface.get_formula(
                    translated_options, epoch_result
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

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None:
        return await self.interface.get_package_detail(translated_options, package)

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail:
        return await self.interface.get_build_context(
            translated_options, package, runtime_product_infos
        )

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_context_info: BuildContextInfo,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo:
        return await self.interface.compute_product_info(
            translated_options, package, build_context_info, runtime_product_infos
        )


async def create_repository(
    context_stack: AsyncExitStack,
    repository_config: RepositoryConfig,
    drivers: Mapping[str, RepositoryDriverConfig],
    data_path: Path,
) -> RepositoryInterface:
    return await context_stack.enter_async_context(
        LocalRepository.create(repository_config, drivers, data_path)
    )


@asynccontextmanager
async def Repositories(
    drivers: Mapping[str, RepositoryDriverConfig],
    repository_configs: Iterable[RepositoryConfig],
    data_path: Path,
) -> AsyncGenerator[Iterable[Repository], None]:
    async with AsyncExitStack() as context_stack:
        yield [
            await Repository.create(
                config,
                await create_repository(
                    context_stack,
                    config,
                    drivers,
                    data_path / "repository" / str(index),
                ),
                data_path,
                index,
            )
            for index, config in enumerate(repository_configs)
        ]
