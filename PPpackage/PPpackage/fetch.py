from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, MutableMapping
from itertools import islice
from pathlib import Path
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes
from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    ProductIDAndInfo,
)
from PPpackage_utils.utils import TemporaryDirectory

from PPpackage.fetch_helpers import fetch_install_generate

from .submanager import Submanager
from .utils import NodeData, SubmanagerCommandFailure


def create_dependencies(node_dependencies: Iterable[tuple[ManagerAndName, NodeData]]):
    return [
        Dependency(
            manager=manager_and_name.manager,
            name=manager_and_name.name,
            product_info=data["product_info"],
        )
        for manager_and_name, data in node_dependencies
    ]


def graph_successors(
    graph: MultiDiGraph, node: Any
) -> Iterable[tuple[ManagerAndName, NodeData]]:
    for node in islice(dfs_preorder_nodes(graph, source=node), 1, None):
        yield node, graph.nodes[node]


async def fetch_manager(
    workdir_path: Path,
    submanagers: Mapping[str, Submanager],
    submanager_name: str,
    meta_options: Mapping[str, Options],
    package: Package,
    dependencies: Iterable[Dependency],
    nodes: Mapping[Any, NodeData],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
):
    submanager = submanagers[submanager_name]
    options = meta_options.get(submanager.name)

    async with submanager.fetch(
        options, package, dependencies, None, None
    ) as result_first:
        if isinstance(result_first, ProductIDAndInfo):
            id_and_info = result_first
        else:
            generators = result_first
            meta_dependencies = packages_to_dependencies[
                ManagerAndName(submanager.name, package.name)
            ]

            with (
                TemporaryDirectory(workdir_path) as installation_path,
                TemporaryDirectory(workdir_path) as generators_path,
            ):
                await fetch_install_generate(
                    submanagers,
                    meta_options,
                    install_order,
                    meta_dependencies,
                    generators,
                    installation_path,
                    generators_path,
                )

                async with submanager.fetch(
                    options, package, dependencies, installation_path, generators_path
                ) as result_second:
                    if isinstance(result_second, ProductIDAndInfo):
                        id_and_info = result_second
                    else:
                        raise SubmanagerCommandFailure("Fetch failed.")

    node = nodes[ManagerAndName(submanager.name, package.name)]
    node["product_id"] = id_and_info.product_id
    node["product_info"] = id_and_info.product_info

    stderr.write(f"{submanager.name}: {package.name} -> {id_and_info.product_id}\n")


async def fetch(
    workdir_path: Path,
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    graph: MultiDiGraph,
    fetch_order: Iterable[Iterable[tuple[ManagerAndName, NodeData]]],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
):
    stderr.write("Fetching packages...\n")

    packages_to_dependencies: MutableMapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ] = {}

    for generation in fetch_order:
        async with TaskGroup() as group:
            for node, data in generation:
                node_dependencies = list(graph_successors(graph, node))

                dependencies = create_dependencies(node_dependencies)

                packages_to_dependencies[node] = node_dependencies

                group.create_task(
                    fetch_manager(
                        workdir_path,
                        submanagers,
                        node.manager,
                        meta_options,
                        Package(name=node.name, version=data["version"]),
                        dependencies,
                        graph.nodes,
                        packages_to_dependencies,
                        install_order,
                    )
                )
