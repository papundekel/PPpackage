from asyncio import TaskGroup
from collections.abc import Iterable, MutableMapping
from functools import singledispatch
from hashlib import sha1
from itertools import islice
from pathlib import Path
from shutil import move
from sys import stderr
from tempfile import mkdtemp
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    DependencyProductInfos,
    ProductDetail,
)
from pydantic import AnyUrl
from sqlitedict import SqliteDict

from PPpackage.utils.validation import save_to_string

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .schemes import NodeData


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


async def download_file(source_url: AnyUrl, destination_path: Path, client: HTTPClient):
    async with client.stream("GET", str(source_url), follow_redirects=True) as response:
        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"Failed to fetch archive {source_url}."
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
) -> None:
    raise NotImplementedError


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
    product_detail: ArchiveProductDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    await fetch_archive(product_detail.archive, destination_path, client, repository)

    return product_detail.installer


def create_dependency_product_infos(
    dependencies: Iterable[tuple[str, NodeData]]
) -> DependencyProductInfos:
    dependency_product_infos = dict[str, MutableMapping[str, Any]]()

    for dependency, node_data in dependencies:
        for interface in node_data["detail"].interfaces:
            dependency_product_infos.setdefault(interface, {})[dependency] = node_data[
                "product_info"
            ].get(interface)

    return dependency_product_infos


async def fetch_package_or_cache(
    cache_mapping: SqliteDict,
    cache_path: Path,
    client: HTTPClient,
    package: str,
    node_data: NodeData,
    dependencies: Iterable[tuple[str, NodeData]],
) -> tuple[Path, str]:
    repository = node_data["repository"]
    dependency_product_infos = create_dependency_product_infos(dependencies)

    product_info = await repository.compute_product_info(
        package, dependency_product_infos
    )
    node_data["product_info"] = product_info

    hasher = sha1()
    hasher.update(package.encode())
    hasher.update(save_to_string(product_info).encode())
    product_info_hash = hasher.hexdigest()

    if product_info_hash not in cache_mapping:
        product_path = Path(mkdtemp(dir=cache_path)) / "product"
        installer = await fetch_package(
            node_data["detail"].product,
            client,
            package,
            repository,
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


async def fetch(
    cache_mapping: SqliteDict, cache_path: Path, client: HTTPClient, graph: MultiDiGraph
) -> None:
    stderr.write("Fetching package products...\n")

    for generation in topological_generations(graph.reverse(copy=False)):
        async with TaskGroup() as group:
            for package in generation:
                node_data: NodeData = graph.nodes[package]

                dependencies = graph_successors(graph, package)

                node_data["product_task"] = group.create_task(
                    fetch_package_or_cache(
                        cache_mapping,
                        cache_path,
                        client,
                        package,
                        node_data,
                        dependencies,
                    )
                )

        for package in generation:
            node_data = graph.nodes[package]

            node_data["product"] = node_data["product_task"].result()

    stderr.write("Package products fetched.\n")
