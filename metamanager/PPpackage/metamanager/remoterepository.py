from logging import getLogger
from typing import Any, AsyncIterable

from hishel import AsyncCacheClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import FetchPackageInfo, Requirement

from PPpackage.utils.validation import load_from_bytes

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .schemes import RemoteRepositoryConfig
from .utils import HTTPResponseReader

logger = getLogger(__name__)


class RemoteRepository(Repository):
    def __init__(self, config: RemoteRepositoryConfig, client: HTTPClient):
        self.client = client

        self.url = str(config.url).rstrip("/")

    async def fetch_packages(self) -> AsyncIterable[FetchPackageInfo]:
        async with self.client.stream(
            "GET",
            f"{self.url}/fetch-packages",
            headers={"Cache-Control": "no-cache"},
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote repository.fetch_packages failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            async for package in reader.load_many(FetchPackageInfo):
                yield package

    async def translate_options(self, options: Any) -> Any:
        response = await self.client.get(
            f"{self.url}/translate-options",
            params={"options": options},
            headers={"Cache-Control": "no-cache"},
            timeout=None,
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"remote repository.translate_options failed {(await response.aread()).decode()}"
            )

        return load_from_bytes(Any, memoryview(response.read()))  # type: ignore

    async def fetch_formula(
        self,
        translated_options: Any,
    ) -> AsyncIterable[Requirement]:
        async with self.client.stream(
            "GET",
            f"{self.url}/fetch-formula",
            params={"translated_options": translated_options},
            headers={"Cache-Control": "no-cache"},
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote repository.fetch_formula failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            async for requirement in reader.load_many(Requirement):  # type: ignore
                yield requirement
