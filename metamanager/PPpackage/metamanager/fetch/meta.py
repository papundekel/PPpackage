from collections.abc import Awaitable, Iterable, Mapping, Set
from pathlib import Path
from typing import Any

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import (
    BuildContextInfo,
    MetaBuildContextDetail,
)

from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.metamanager.translators import Translator

from . import fetch_package, get_build_context_info, process_build_context


@process_build_context.register
async def process_build_context_meta(
    repositories: Iterable[Repository],
    translators_task: Awaitable[Mapping[str, Translator]],
    build_context: MetaBuildContextDetail,
    build_options: Any,
) -> tuple[Mapping[Repository, Any], Set[str]]:
    from PPpackage.metamanager.resolve import resolve

    repository_to_translated_options, model = await resolve(
        repositories, translators_task, build_options, build_context.requirement
    )

    return repository_to_translated_options, model


@fetch_package.register
async def fetch_package_meta(
    build_context: MetaBuildContextDetail,
    processed_data: tuple[Mapping[Repository, Any], Set[str]],
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    repository_to_translated_options, model = processed_data

    return "simple"


@get_build_context_info.register
async def get_build_context_info_meta(
    build_context: MetaBuildContextDetail,
    processed_data: tuple[Mapping[Repository, Any], Set[str]],
) -> BuildContextInfo:
    _, model = processed_data

    return {"packages": model}
