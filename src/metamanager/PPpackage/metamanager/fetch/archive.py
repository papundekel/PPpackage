from collections.abc import Awaitable, Iterable, Mapping
from pathlib import Path
from shutil import move
from typing import Any

from httpx import Client as HTTPClient
from networkx import MultiDiGraph
from PPpackage.repository_driver.interface.schemes import (
    ArchiveBuildContextDetail,
    BuildContextInfo,
)
from pydantic import AnyUrl
from sqlitedict import SqliteDict

from PPpackage.metamanager.exceptions import SubmanagerCommandFailure
from PPpackage.metamanager.installer import Installer
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.translators import Translator
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.container import Containerizer

from . import fetch_package, get_build_context_info, process_build_context


async def download_file(source_url: AnyUrl, destination_path: Path, client: HTTPClient):
    with client.stream(
        "GET", str(source_url), follow_redirects=True, timeout=None
    ) as response:
        if response.status_code != 200:
            raise SubmanagerCommandFailure(
                f"Failed to fetch archive {source_url}.\n"
                f"{(response.read()).decode()}"
            )

        with destination_path.open("wb") as file:
            file.write(response.read())


@process_build_context.register
async def process_build_context_archive(
    build_context: ArchiveBuildContextDetail,
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    build_options: Any,
    graph: MultiDiGraph,
    package: str,
) -> None:
    return None


@fetch_package.register
async def fetch_package_archive(
    build_context: ArchiveBuildContextDetail,
    processed_data: None,
    containerizer: Containerizer,
    containerizer_workdir: Path,
    archive_client: HTTPClient,
    cache_mapping: SqliteDict,
    product_cache_path: Path,
    installers: Mapping[str, Installer],
    package: str,
    destination_path: Path,
) -> str:
    match build_context.archive:
        case AnyUrl() as archive_url:
            await download_file(archive_url, destination_path, archive_client)
        case archive_path:
            move(archive_path, destination_path)

    return build_context.installer


@get_build_context_info.register
async def get_build_context_info_archive(
    build_context: ArchiveBuildContextDetail, processed_data: None
) -> BuildContextInfo:
    return {}
