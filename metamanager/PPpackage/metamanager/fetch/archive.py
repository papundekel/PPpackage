from collections.abc import Iterable
from functools import singledispatch
from pathlib import Path
from shutil import move

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import ArchiveBuildContextDetail
from pydantic import AnyUrl

from PPpackage.metamanager.exceptions import SubmanagerCommandFailure
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData

from . import fetch_package


async def download_file(source_url: AnyUrl, destination_path: Path, client: HTTPClient):
    async with client.stream("GET", str(source_url), follow_redirects=True) as response:
        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"Failed to fetch archive {source_url}.\n"
                f"{(await response.aread()).decode()}"
            )

        with destination_path.open("wb") as file:
            async for chunk in response.aiter_raw():
                file.write(chunk)


@singledispatch
async def fetch_archive(
    source_url_or_path: AnyUrl | Path,
    destination_path: Path,
    client: HTTPClient,
    repository: Repository,
) -> None: ...


@fetch_archive.register
async def _(
    source_url: AnyUrl,
    destination_path: Path,
    client: HTTPClient,
    repository: Repository,
):
    await download_file(source_url, destination_path, client)


@fetch_archive.register
async def _(
    source_path: Path,
    destination_path: Path,
    client: HTTPClient,
    repository: Repository,
):
    url = repository.get_url()

    if url is None:
        move(source_path, destination_path)
    else:
        await download_file(
            AnyUrl.build(scheme=url.scheme, host=str(url.host), path=str(source_path)),
            destination_path,
            client,
        )


@fetch_package.register
async def _(
    product_detail: ArchiveBuildContextDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    await fetch_archive(product_detail.archive, destination_path, client, repository)

    return product_detail.installer
