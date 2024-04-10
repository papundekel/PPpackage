from logging import getLogger
from typing import Any, AsyncIterable

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import FetchPackageInfo, Requirement

from PPpackage.utils.validation import save_object

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
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote repository.fetch_packages failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            return reader.load_many(FetchPackageInfo)

    async def translate_options(self, options: Any) -> Any:
        async with self.client.stream(
            "GET",
            f"{self.url}/fetch-packages",
            params=save_object(options),
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote repository.translate_options failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            return await reader.load_one(Any)  # type: ignore

    async def fetch_formula(
        self,
        translated_options: Any,
    ) -> AsyncIterable[Requirement]:
        async with self.client.stream(
            "GET",
            f"{self.url}/fetch-packages",
            params=save_object(translated_options),
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote repository.fetch_packages failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            return reader.load_many(Requirement)  # type: ignore
