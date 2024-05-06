from logging import getLogger
from typing import Any, AsyncIterable

from hishel import AsyncCacheClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    BuildContextInfo,
    PackageDetail,
    ProductInfo,
    ProductInfos,
    Requirement,
    TranslatorInfo,
)

from PPpackage.metamanager.exceptions import SubmanagerCommandFailure
from PPpackage.metamanager.schemes import RemoteRepositoryConfig
from PPpackage.metamanager.utils import HTTPResponseReader
from PPpackage.utils.utils import Result
from PPpackage.utils.validation import dump_json, validate_json

from .interface import RepositoryInterface

logger = getLogger(__name__)


class RemoteRepository(RepositoryInterface):
    def __init__(self, config: RemoteRepositoryConfig, client: HTTPClient):
        self.client = client

        self.url = str(config.url).rstrip("/")

    def get_identifier(self) -> str:
        return self.url

    def get_url(self) -> str:
        return self.url

    async def get_epoch(self) -> str:
        response = await self.client.head(f"{self.url}/translate-options")

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.get_epoch failed "
                f"{(await response.aread()).decode()}"
            )

        return response.headers["ETag"]

    async def fetch_translator_data(
        self, epoch_result: Result[str]
    ) -> AsyncIterable[TranslatorInfo]:
        async with self.client.stream(
            "GET",
            f"{self.url}/translator-info",
            headers={"Cache-Control": "no-cache"},
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    "remote repository.fetch_translator_data failed "
                    f"{(await response.aread()).decode()}"
                )

            epoch_result.set(response.headers["ETag"])

            reader = HTTPResponseReader(response)

            async for package in reader.load_many(TranslatorInfo):
                yield package

    async def translate_options(self, options: Any) -> tuple[str, Any]:
        response = await self.client.get(
            f"{self.url}/translate-options",
            params={"options": dump_json(options)},
            headers={"Cache-Control": "no-cache"},
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.translate_options failed "
                f"{(await response.aread()).decode()}"
            )

        return response.headers["ETag"], validate_json(Any, memoryview(response.read()))  # type: ignore

    async def get_formula(
        self, translated_options: Any, epoch_result: Result[str]
    ) -> AsyncIterable[Requirement]:
        async with self.client.stream(
            "GET",
            f"{self.url}/formula",
            params={"translated_options": dump_json(translated_options)},
            headers={"Cache-Control": "no-cache"},
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    "remote repository.get_formula failed "
                    f"{(await response.aread()).decode()}"
                )

            epoch_result.set(response.headers["ETag"])

            reader = HTTPResponseReader(response)

            async for requirement in reader.load_many(Requirement):  # type: ignore
                yield requirement

    async def get_package_detail(
        self, translated_options: Any, package: str
    ) -> PackageDetail | None:
        response = await self.client.get(
            f"{self.url}/packages/{package}",
            params={"translated_options": dump_json(translated_options)},
        )

        if response.status_code == 404:
            return None

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.get_package_detail failed "
                f"{(await response.aread()).decode()}"
            )

        return validate_json(PackageDetail, memoryview(response.read()))

    async def get_build_context(
        self,
        translated_options: Any,
        package: str,
        runtime_product_infos: ProductInfos,
    ) -> BuildContextDetail:
        response = await self.client.get(
            f"{self.url}/packages/{package}/product-info",
            params={
                "translated_options": dump_json(translated_options),
                "runtime_product_infos": dump_json(runtime_product_infos),
            },
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.compute_product_info failed "
                f"{(await response.aread()).decode()}"
            )

        return validate_json(BuildContextDetail, memoryview(response.read()))  # type: ignore

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        build_context_info: BuildContextInfo,
        runtime_product_infos: ProductInfos,
    ) -> ProductInfo:
        response = await self.client.get(
            f"{self.url}/packages/{package}/product-info",
            params={
                "translated_options": dump_json(translated_options),
                "build_context_info": dump_json(build_context_info),
                "runtime_product_infos": dump_json(runtime_product_infos),
            },
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.compute_product_info failed "
                f"{(await response.aread()).decode()}"
            )

        return validate_json(ProductInfo, memoryview(response.read()))  # type: ignore
