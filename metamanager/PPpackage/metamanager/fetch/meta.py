from collections.abc import Awaitable, Iterable, Mapping, Set
from itertools import chain
from pathlib import Path
from shutil import move
from sys import stderr
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph
from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    BuildContextInfo,
    MetaBuildContextDetail,
    SimpleRequirement,
)
from sqlitedict import SqliteDict

from metamanager.PPpackage.metamanager.installer import Installer
from PPpackage.metamanager.graph import get_graph_items
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.metamanager.translators import Translator
from PPpackage.utils.utils import TemporaryDirectory

from . import fetch_package, get_build_context_info, process_build_context


@process_build_context.register
async def process_build_context_meta(
    build_context: MetaBuildContextDetail,
    repositories: Iterable[Repository],
    translators_task: Awaitable[Mapping[str, Translator]],
    build_options: Any,
    graph: MultiDiGraph,
) -> tuple[
    Mapping[Repository, Any],
    Iterable[Repository],
    Awaitable[Mapping[str, Translator]],
    Any,
    Set[str],
]:
    from PPpackage.metamanager.resolve import resolve

    requirement = (
        build_context.requirement
        if not build_context.on_top
        else ANDRequirement(
            list(
                chain(
                    [build_context.requirement],
                    (
                        SimpleRequirement("noop", package)
                        for package, _ in get_graph_items(graph)
                    ),
                )
            )
        )
    )

    repository_to_translated_options, model = await resolve(
        repositories, translators_task, build_options, requirement
    )

    return (
        repository_to_translated_options,
        repositories,
        translators_task,
        build_options,
        model,
    )


@fetch_package.register
async def fetch_package_meta(
    build_context: MetaBuildContextDetail,
    processed_data: tuple[
        Mapping[Repository, Any],
        Iterable[Repository],
        Awaitable[Mapping[str, Translator]],
        Any,
        Set[str],
    ],
    containerizer: Containerizer,
    archive_client: HTTPClient,
    cache_mapping: SqliteDict,
    product_cache_path: Path,
    installers: Mapping[str, Installer],
    package: str,
    repository: Repository,
    destination_path: Path,
) -> str:
    from PPpackage.metamanager.fetch_and_install import fetch_and_install

    (
        repository_to_translated_options,
        repositories,
        translators_task,
        build_options,
        model,
    ) = processed_data

    with TemporaryDirectory() as build_context_root_path:
        await fetch_and_install(
            containerizer,
            archive_client,
            cache_mapping,
            product_cache_path,
            repositories,
            repository_to_translated_options,
            translators_task,
            installers,
            build_context_root_path,
            None,
            build_options,
            model,
        )

        print(
            f"Building package {package} with {build_context.command}...", file=stderr
        )

        return_code = containerizer.run(
            build_context.command,
            stdin=None,
            rootfs=str(containerizer.translate(build_context_root_path)),
        )

        if return_code != 0:
            raise Exception("Failed to build package")

        move(build_context_root_path / "mnt" / "output" / "product", destination_path)

        with (build_context_root_path / "mnt" / "output" / "installer").open(
            "r"
        ) as file:
            installer = file.read()

    return installer


@get_build_context_info.register
async def get_build_context_info_meta(
    build_context: MetaBuildContextDetail,
    processed_data: tuple[Any, Any, Any, Any, Set[str]],
) -> BuildContextInfo:
    _, _, _, _, model = processed_data

    return {"packages": model}
