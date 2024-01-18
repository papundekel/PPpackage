from collections.abc import AsyncGenerator, Iterable, Set
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterable, Self

from httpx import AsyncClient as HTTPClient
from PPpackage_submanager.schemes import (
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    Product,
    ResolutionGraph,
)
from PPpackage_utils.stream import dump_bytes_chunked, dump_loop, dump_many, dump_one
from PPpackage_utils.tar import archive as tar_archive
from PPpackage_utils.tar import extract as tar_extract
from PPpackage_utils.validation import load_from_bytes

from PPpackage.schemes import RemoteSubmanagerConfig
from PPpackage.utils import SubmanagerCommandFailure

from .submanager import Submanager
from .utils import HTTPResponseReader


class RemoteSubmanager(Submanager):
    def __init__(self, name: str, client: HTTPClient, config: RemoteSubmanagerConfig):
        super().__init__(name)

        self.client = client

        self.url = str(config.url).rstrip("/")

        with config.token_path.open("r") as token_file:
            self.token = token_file.read().strip()

    async def update_database(self) -> None:
        pass

    async def resolve(
        self,
        options: Options,
        requirements_list: Iterable[Iterable[Any]],
    ) -> AsyncIterable[ResolutionGraph]:
        async def content():
            for chunk in dump_one(options):
                yield chunk

            for chunk in dump_loop(
                (chunk for chunk in dump_many(requirements))
                for requirements in requirements_list
            ):
                yield chunk

        async with self.client.stream(
            "POST",
            f"{self.url}/resolve",
            headers={"Authorization": f"Bearer {self.token}"},
            content=content(),
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure(
                    f"remote resolve failed {(await response.aread()).decode()}"
                )

            reader = HTTPResponseReader(response)

            async for resolution_graph in reader.load_many(ResolutionGraph):
                yield resolution_graph

    @asynccontextmanager
    async def fetch(
        self,
        options: Options,
        package: Package,
        dependencies: Iterable[Dependency],
        installation_path: Path | None,
        generators_path: Path | None,
    ) -> AsyncGenerator[PackageIDAndInfo | AsyncIterable[str], None]:
        installation = (
            tar_archive(installation_path) if installation_path is not None else None
        )
        generators = (
            tar_archive(generators_path) if generators_path is not None else None
        )

        async def content():
            for chunk in dump_one(options):
                yield chunk

            if installation is not None:
                for chunk in dump_bytes_chunked(installation):
                    yield chunk

            if generators is not None:
                for chunk in dump_bytes_chunked(generators):
                    yield chunk

            for chunk in dump_many(dependencies):
                yield chunk

        async with self.client.stream(
            "POST",
            f"{self.url}/products",
            headers={"Authorization": f"Bearer {self.token}"},
            params={
                "package_name": package.name,
                "package_version": package.version,
                "installation_present": installation_path is not None,
                "generators_present": generators_path is not None,
            },
            content=content(),
            timeout=None,
        ) as response:
            reader = HTTPResponseReader(response)

            if response.is_success:
                yield await reader.load_one(PackageIDAndInfo)
            elif response.status_code == 422:
                yield reader.load_many(str)
            else:
                raise SubmanagerCommandFailure(
                    f"remote fetch failed: {(await response.aread()).decode()}"
                )

    async def install(self, id: str, installation_path: Path, product: Product) -> None:
        response = await self.client.patch(
            f"{self.url}/installations/{id}",
            headers={"Authorization": f"Bearer {self.token}"},
            params={
                "package_name": product.name,
                "package_version": product.version,
                "product_id": product.product_id,
            },
            timeout=None,
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"remote install failed: {(await response.aread()).decode()}"
            )

    async def install_post(self, installation: memoryview) -> str:
        async def content():
            for chunk in dump_bytes_chunked(installation):
                yield chunk

        response = await self.client.post(
            f"{self.url}/installations",
            headers={"Authorization": f"Bearer {self.token}"},
            content=content(),
            timeout=None,
        )

        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"remote install post failed: {(await response.aread()).decode()}"
            )

        response_bytes = await response.aread()
        id = load_from_bytes(str, memoryview(response_bytes))

        return id

    async def install_init(self, installation_path: Path) -> str:
        installation = tar_archive(installation_path)

        return await self.install_post(installation)

    async def install_get(self, id: str) -> memoryview:
        async with self.client.stream(
            "GET",
            f"{self.url}/installations/{id}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure("remote install_send failed")

            reader = HTTPResponseReader(response)

            installation = await reader.load_bytes_chunked()

        return installation

    async def install_send(
        self,
        source_id: str,
        destination: Self,
        destination_id: str | None,
        installation_path: Path,
    ) -> str:
        installation = await self.install_get(source_id)

        return await destination.install_receive(
            destination_id, installation, installation_path
        )

    async def install_receive(
        self,
        destination_id: str | None,
        installation: memoryview | None,
        installation_path: Path,
    ) -> str:
        if installation is None:
            installation = tar_archive(installation_path)

        if destination_id is not None:
            response = await self.client.put(
                f"{self.url}/installations/{destination_id}",
                content=dump_bytes_chunked(installation),
                timeout=None,
            )

            if not response.is_success:
                raise SubmanagerCommandFailure("remote install_receive failed")
        else:
            destination_id = await self.install_post(installation)

        return destination_id

    async def install_download(self, id: str, installation_path: Path) -> None:
        installation = await self.install_get(id)

        tar_extract(installation, installation_path)

    async def install_delete(self, id: str) -> None:
        response = await self.client.delete(
            f"{self.url}/installations/{id}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=None,
        )

        if not response.is_success:
            raise SubmanagerCommandFailure("remote install_delete failed")

    async def generate(
        self,
        options: Options,
        products: Iterable[Product],
        generators: Set[str],
        destination_path: Path,
    ) -> None:
        async def content():
            for chunk in dump_one(options):
                yield chunk

            for chunk in dump_many(products):
                yield chunk

            for chunk in dump_many(generators):
                yield chunk

        async with self.client.stream(
            "POST",
            f"{self.url}/generators",
            headers={"Authorization": f"Bearer {self.token}"},
            content=content(),
            timeout=None,
        ) as response:
            if not response.is_success:
                raise SubmanagerCommandFailure("remote generate failed")

            reader = HTTPResponseReader(response)

            generators_bytes = await reader.load_bytes_chunked()

        tar_extract(generators_bytes, destination_path)
        tar_extract(generators_bytes, destination_path)
