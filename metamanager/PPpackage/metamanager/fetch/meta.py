from collections.abc import Awaitable, Iterable, Mapping, Set
from itertools import chain
from os import chmod
from pathlib import Path
from shutil import move
from sys import stderr
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph
from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import (
    BuildContextInfo,
    MetaBuildContextDetail,
    Requirement,
)
from sqlitedict import SqliteDict

from metamanager.PPpackage.metamanager.installer import Installer
from PPpackage.metamanager.graph import successors as graph_successors
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.translators import Translator
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.utils import TemporaryDirectory

from . import fetch_package, get_build_context_info, process_build_context


@process_build_context.register
async def process_build_context_meta(
    build_context: MetaBuildContextDetail,
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    build_options: Any,
    graph: MultiDiGraph,
    package: str,
) -> tuple[
    Mapping[Repository, Any],
    Iterable[Repository],
    Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    Any,
    Set[str],
]:
    from PPpackage.metamanager.resolve import resolve

    requirements = (
        build_context.requirements
        if not build_context.on_top
        else chain(
            build_context.requirements,
            (
                Requirement("noop", package)
                for package, _ in graph_successors(graph, package)
            ),
        )
    )

    repository_to_translated_options, model = await resolve(
        containerizer,
        containerizer_workdir,
        repositories,
        translators_task,
        build_options,
        requirements,
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
        Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
        Any,
        Set[str],
    ],
    containerizer: Containerizer,
    containerizer_workdir: Path,
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

    with TemporaryDirectory(containerizer_workdir) as build_context_root_path:
        stderr.write(f"Fetching and installing build context for {package}...\n")

        chmod(build_context_root_path, 0o755)

        await fetch_and_install(
            containerizer,
            containerizer_workdir,
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

        stderr.write(f"Building package {package}...\n")

        return_code = containerizer.run(
            build_context.command,
            stdin=None,
            rootfs=str(containerizer.translate(build_context_root_path)),
        )

        if return_code != 0:
            raise Exception(
                f"Failed to build package {package}, return code: {return_code}"
            )

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
