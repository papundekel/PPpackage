from collections.abc import Iterable, Mapping
from pathlib import Path
from shutil import move

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import (
    ArchiveBuildContextDetail,
    BuildContextInfo,
)
from pydantic import AnyUrl

from PPpackage.metamanager.exceptions import SubmanagerCommandFailure
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.metamanager.translators import Translator

from . import fetch_package, get_build_context_info, process_build_context


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


@process_build_context.register
async def process_build_context_archive(
    repositories: Iterable[Repository],
    translators: Mapping[str, Translator],
    build_context: ArchiveBuildContextDetail,
):
    return None


@fetch_package.register
async def fetch_package_archive(
    build_context: ArchiveBuildContextDetail,
    processed_data: None,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    repository_url = repository.get_url()

    match build_context.archive, repository_url:
        case AnyUrl() as archive_url, _:
            await download_file(archive_url, destination_path, client)
        case archive_path, AnyUrl():
            await download_file(
                AnyUrl.build(
                    scheme=repository_url.scheme,
                    host=str(repository_url.host),
                    path=str(archive_path),
                ),
                destination_path,
                client,
            )
        case archive_path, _:
            move(archive_path, destination_path)

    return build_context.installer


@get_build_context_info.register
async def get_build_context_info_archive(
    build_context: ArchiveBuildContextDetail, processed_data: None
) -> BuildContextInfo:
    return {}
