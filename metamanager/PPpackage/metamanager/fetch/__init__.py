from asyncio import create_task
from collections.abc import Iterable, MutableMapping
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
    DependencyProductInfos,
    ProductDetail,
    ProductInfo,
)
from sqlitedict import SqliteDict

from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData
from PPpackage.utils.validation import dump_json


@singledispatch
async def fetch_package(
    product_detail: ProductDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[str],
    destination_path: Path,
) -> str:
    raise NotImplementedError


from .archive import _
from .meta_on_top import _


async def create_dependency_product_infos(
    dependencies: Iterable[tuple[str, NodeData]]
) -> DependencyProductInfos:
    dependency_product_infos = dict[str, MutableMapping[str, Any]]()

    for dependency, node_data in dependencies:
        for interface in node_data["detail"].interfaces:
            dependency_product_infos.setdefault(interface, {})[dependency] = (
                await node_data["product_info"]
            ).get(interface)

    return dependency_product_infos


async def compute_product_info(
    package: str, repository: Repository, dependencies: Iterable[tuple[str, NodeData]]
) -> ProductInfo:
    dependency_product_infos = await create_dependency_product_infos(dependencies)

    product_info = await repository.compute_product_info(
        package, dependency_product_infos
    )

    return product_info


def hash_product_info(package: str, product_info: ProductInfo) -> str:
    hasher = sha1()
    hasher.update(package.encode())
    hasher.update(dump_json(product_info).encode())
    return hasher.hexdigest()


async def fetch_package_or_cache(
    cache_mapping: SqliteDict,
    cache_path: Path,
    client: HTTPClient,
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
            node_data["detail"].product,
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

            node_data["product_info"] = create_task(
                compute_product_info(package, node_data["repository"], dependencies)
            )

            node_data["product"] = create_task(
                fetch_package_or_cache(
                    cache_mapping,
                    cache_path,
                    client,
                    package,
                    node_data,
                    dependencies,
                )
            )
