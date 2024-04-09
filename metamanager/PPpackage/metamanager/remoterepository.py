from logging import getLogger
from typing import Any, AsyncIterable

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import PackageVersion

from PPpackage.utils.stream import dump_one

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .schemes import RemoteRepositoryConfig
from .utils import HTTPResponseReader

logger = getLogger(__name__)


class RemoteRepository(Repository):
    def __init__(self, config: RemoteRepositoryConfig, client: HTTPClient):
        self.client = client

        self.url = str(config.url).rstrip("/")

    async def translate_options(self, options: Any) -> Any:
        pass  # TODO

    async def fetch_packages(
        self,
        translated_options: Any,
    ) -> AsyncIterable[PackageVersion]:
        async with self.client.stream(
            "GET",
            f"{self.url}/fetch-packages",
            content=dump_one(translated_options),
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote resolve failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            return reader.load_many(PackageVersion)
