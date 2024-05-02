from logging import getLogger
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, AsyncIterable

from hishel import AsyncCacheClient as HTTPClient

from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    DependencyProductInfos,
    PackageDetail,
    ProductInfo,
    Requirement,
    TranslatorInfo,
)
from PPpackage.utils.utils import Result
from PPpackage.utils.validation import dump_json, validate_json

from .exceptions import SubmanagerCommandFailure
from .repository import RepositoryInterface
from .schemes import RemoteRepositoryConfig
from .utils import HTTPResponseReader

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

        reader = HTTPResponseReader(response)

        package_detail = await reader.load_one(PackageDetail)

        if (
            package_detail is not None
            and isinstance(package_detail.product, ArchiveProductDetail)
            and isinstance(package_detail.product.archive, Path)
        ):
            archive_bytes = await reader.load_bytes_chunked()

            archive_directory_path = Path(mkdtemp())
            archive_path = archive_directory_path / "archive"
            with archive_path.open("wb") as file:
                file.write(archive_bytes)

            return PackageDetail(
                package_detail.interfaces,
                package_detail.dependencies,
                ArchiveProductDetail(archive_path, package_detail.product.installer),
            )

        return package_detail

    async def compute_product_info(
        self,
        translated_options: Any,
        package: str,
        dependency_product_infos: DependencyProductInfos,
    ) -> ProductInfo:
        response = await self.client.get(
            f"{self.url}/packages/{package}/product-info",
            params={
                "translated_options": dump_json(translated_options),
                "dependency_product_infos": dump_json(dependency_product_infos),
            },
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                "remote repository.compute_product_info failed "
                f"{(await response.aread()).decode()}"
            )

        return validate_json(ProductInfo, memoryview(response.read()))  # type: ignore
