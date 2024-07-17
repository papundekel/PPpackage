from asyncio import TaskGroup
from collections.abc import Awaitable, Iterable, Mapping
from pathlib import Path
from typing import Any

from httpx import Client as HTTPClient
from networkx import MultiDiGraph
from sqlitedict import SqliteDict

from PPpackage.metamanager.installer import Installer
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.translators import Translator
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.container import Containerizer

from .fetch import fetch
from .install import install


async def fetch_and_install(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    repository_to_translated_options: Mapping[Repository, Any],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    installers: Mapping[str, Installer],
    cache_mapping: SqliteDict,
    archive_client: HTTPClient,
    cache_path: Path,
    build_options: Any,
    installation_path: Path,
    graph: MultiDiGraph,
):
    async with TaskGroup() as task_group:
        fetch(
            task_group,
            containerizer,
            containerizer_workdir,
            repositories,
            repository_to_translated_options,
            translators_task,
            installers,
            cache_mapping,
            archive_client,
            cache_path,
            build_options,
            graph,
        )

        await install(installers, graph, installation_path)
