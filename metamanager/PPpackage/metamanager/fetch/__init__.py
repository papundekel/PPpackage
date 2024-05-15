from asyncio import Lock, TaskGroup
from collections.abc import Awaitable, Iterable, Mapping, MutableMapping, Set
from contextlib import asynccontextmanager
from functools import singledispatch
from hashlib import sha1
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, topological_generations
from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    BuildContextInfo,
    ProductInfo,
    ProductInfos,
)
from sqlitedict import SqliteDict

from PPpackage.metamanager.graph import successors as graph_successors
from PPpackage.metamanager.installer import Installer
from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.metamanager.translators import Translator
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.utils import lock_by_key, rmtree
from PPpackage.utils.validation import dump_json


@singledispatch
async def process_build_context(
    build_context: BuildContextDetail,
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    build_options: Any,
    graph: MultiDiGraph,
    package: str,
) -> Any:
    raise NotImplementedError


@singledispatch
async def fetch_package(
    build_context: BuildContextDetail,
    processed_data: Any,
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
    raise NotImplementedError


@singledispatch
async def get_build_context_info(
    build_context_detail: BuildContextDetail, processed_data: Any
) -> BuildContextInfo:
    raise NotImplementedError


from .archive import (
    fetch_package_archive,
    get_build_context_info_archive,
    process_build_context_archive,
)
from .meta import (
    fetch_package_meta,
    get_build_context_info_meta,
    process_build_context_meta,
)


async def create_dependency_product_infos(
    interface_dependencies: Set[str], dependencies: Iterable[tuple[str, NodeData]]
) -> ProductInfos:
    dependency_product_infos = dict[str, MutableMapping[str, Any]]()

    for dependency, node_data in dependencies:
        product_info = await node_data["product_info"]

        for interface in node_data["detail"].interfaces & interface_dependencies:
            dependency_product_infos.setdefault(interface, {})[dependency] = (
                product_info.get(interface)
            )

    return dependency_product_infos


async def get_build_context(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    package: str,
    runtime_product_infos_task: Awaitable[ProductInfos],
    repository: Repository,
    translated_options: Any,
    build_options: Any,
    graph: MultiDiGraph,
) -> tuple[BuildContextDetail, Any]:
    runtime_product_infos = await runtime_product_infos_task

    build_context = await repository.get_build_context(
        translated_options, package, runtime_product_infos
    )

    build_context_processed_data = await process_build_context(
        build_context,
        containerizer,
        containerizer_workdir,
        repositories,
        translators_task,
        build_options,
        graph,
        package,
    )

    return build_context, build_context_processed_data


async def compute_product_info(
    package: str,
    build_context_task: Awaitable[tuple[BuildContextDetail, Any]],
    runtime_product_infos_task: Awaitable[ProductInfos],
    repository: Repository,
    translated_options: Any,
) -> ProductInfo:
    build_context, build_context_processed_data = await build_context_task

    build_context_info = await get_build_context_info(
        build_context, build_context_processed_data
    )

    product_detail = await repository.compute_product_info(
        translated_options,
        package,
        build_context_info,
        await runtime_product_infos_task,
    )

    return product_detail


def hash_product_info(package: str, product_info: ProductInfo) -> str:
    product_info_json = dump_json(product_info)

    hasher = sha1()
    hasher.update(package.encode())
    hasher.update(product_info_json.encode())
    return hasher.hexdigest()


product_cache_locks = dict[str, Lock]()


async def fetch_package_or_cache(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    cache_mapping: SqliteDict,
    cache_path: Path,
    archive_client: HTTPClient,
    installers: Mapping[str, Installer],
    build_context_task: Awaitable[tuple[BuildContextDetail, Any]],
    package: str,
    node_data: NodeData,
) -> tuple[Path, str]:
    product_info_hash = hash_product_info(package, await node_data["product_info"])

    async with lock_by_key(product_cache_locks, product_info_hash):
        if product_info_hash not in cache_mapping:
            product_directory_path = Path(
                mkdtemp(dir=cache_path, prefix=package.replace("/", "\\"))
            )
            product_path = product_directory_path / "product"

            try:
                build_context, build_context_processed_data = await build_context_task

                installer = await fetch_package(
                    build_context,
                    build_context_processed_data,
                    containerizer,
                    containerizer_workdir,
                    archive_client,
                    cache_mapping,
                    cache_path,
                    installers,
                    package,
                    node_data["repository"],
                    product_path,
                )
            except:
                rmtree(product_directory_path)
                raise

            cache_mapping[product_info_hash] = product_path, installer
            cache_mapping.commit()

            return product_path, installer
        else:
            return cache_mapping[product_info_hash]


def fetch(
    task_group: TaskGroup,
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
    graph: MultiDiGraph,
) -> None:
    for generation in topological_generations(graph.reverse(copy=False)):
        for package in generation:
            node_data: NodeData = graph.nodes[package]

            dependencies = graph_successors(graph, package)

            runtime_product_infos_task = task_group.create_task(
                create_dependency_product_infos(
                    node_data["detail"].dependencies, dependencies
                )
            )

            repository = node_data["repository"]
            translated_options = repository_to_translated_options[repository]

            build_context_task = task_group.create_task(
                get_build_context(
                    containerizer,
                    containerizer_workdir,
                    repositories,
                    translators_task,
                    package,
                    runtime_product_infos_task,
                    repository,
                    translated_options,
                    build_options,
                    graph,
                )
            )

            node_data["product_info"] = task_group.create_task(
                compute_product_info(
                    package,
                    build_context_task,
                    runtime_product_infos_task,
                    repository,
                    translated_options,
                )
            )

            node_data["product"] = task_group.create_task(
                fetch_package_or_cache(
                    containerizer,
                    containerizer_workdir,
                    cache_mapping,
                    cache_path,
                    archive_client,
                    installers,
                    build_context_task,
                    package,
                    node_data,
                )
            )
