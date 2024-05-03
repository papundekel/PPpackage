from asyncio import create_task
from collections.abc import Awaitable, Iterable, MutableMapping, Set
from functools import singledispatch
from hashlib import sha1
from itertools import islice
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    ProductInfo,
    ProductInfos,
)
from sqlitedict import SqliteDict

from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.utils.validation import dump_json


@singledispatch
async def fetch_package(
    build_context_detail: BuildContextDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[str],
    destination_path: Path,
) -> str:
    raise NotImplementedError


from .archive import _
from .meta import _


async def create_dependency_product_infos(
    interface_dependencies: Set[str], dependencies: Iterable[tuple[str, NodeData]]
) -> ProductInfos:
    dependency_product_infos = dict[str, MutableMapping[str, Any]]()

    for dependency, node_data in dependencies:
        for interface in node_data["detail"].interfaces & interface_dependencies:
            dependency_product_infos.setdefault(interface, {})[dependency] = (
                await node_data["product_info"]
            ).get(interface)

    return dependency_product_infos


async def get_build_context(
    package: str,
    runtime_product_infos_task: Awaitable[ProductInfos],
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
) -> BuildContextDetail:
    runtime_product_infos = await runtime_product_infos_task

    build_context = await repository.get_build_context(package, runtime_product_infos)

    return build_context


async def compute_product_info(
    package: str,
    build_context_task: Awaitable[BuildContextDetail],
    runtime_product_infos_task: Awaitable[ProductInfos],
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
) -> ProductInfo:
    build_context = await build_context_task
    runtime_product_infos = await runtime_product_infos_task

    product_detail = await repository.compute_product_info(
        package, {}, runtime_product_infos
    )

    return product_detail


def hash_product_info(package: str, product_info: ProductInfo) -> str:
    hasher = sha1()
    hasher.update(package.encode())
    hasher.update(dump_json(product_info).encode())
    return hasher.hexdigest()


async def fetch_package_or_cache(
    cache_mapping: SqliteDict,
    cache_path: Path,
    client: HTTPClient,
    build_context_task: Awaitable[BuildContextDetail],
    package: str,
    node_data: NodeData,
    dependencies: Iterable[tuple[str, NodeData]],
) -> tuple[Path, str]:
    stderr.write(f"\t{package}\n")

    product_info_hash = hash_product_info(package, await node_data["product_info"])

    if product_info_hash not in cache_mapping:
        product_path = (
            Path(mkdtemp(dir=cache_path, prefix=package.replace("/", "\\"))) / "product"
        )
        installer = await fetch_package(
            await build_context_task,
            client,
            package,
            node_data["repository"],
            dependencies,
            product_path,
        )

        cache_mapping[product_info_hash] = product_path, installer
        cache_mapping.commit()

        return product_path, installer
    else:
        return cache_mapping[product_info_hash]


def graph_successors(
    graph: MultiDiGraph, package: str
) -> Iterable[tuple[str, NodeData]]:
    for successor in islice(dfs_preorder_nodes(graph, source=package), 1, None):
        yield successor, graph.nodes[successor]


def fetch(
    cache_mapping: SqliteDict, client: HTTPClient, cache_path: Path, graph: MultiDiGraph
) -> None:
    stderr.write("Fetching package products...\n")

    for generation in topological_generations(graph.reverse(copy=False)):
        for package in generation:
            node_data: NodeData = graph.nodes[package]

            dependencies = graph_successors(graph, package)

            runtime_product_infos_task = create_task(
                create_dependency_product_infos(
                    node_data["detail"].dependencies, dependencies
                )
            )

            build_context_task = create_task(
                get_build_context(
                    package,
                    runtime_product_infos_task,
                    node_data["repository"],
                    dependencies,
                )
            )

            node_data["product_info"] = create_task(
                compute_product_info(
                    package,
                    build_context_task,
                    runtime_product_infos_task,
                    node_data["repository"],
                    dependencies,
                )
            )

            node_data["product"] = create_task(
                fetch_package_or_cache(
                    cache_mapping,
                    cache_path,
                    client,
                    build_context_task,
                    package,
                    node_data,
                    dependencies,
                )
            )
