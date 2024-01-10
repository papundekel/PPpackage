from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, MutableMapping
from itertools import islice
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes
from PPpackage_submanager.schemes import Dependency, ManagerAndName, Package

from .submanager import Submanager
from .utils import NodeData


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


async def fetch(
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Mapping[str, Any] | None],
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

                submanager_name = node.manager
                submanager = submanagers[submanager_name]

                group.create_task(
                    submanager.fetch(
                        meta_options.get(submanager_name),
                        Package(name=node.name, version=data["version"]),
                        dependencies,
                        graph.nodes,
                        packages_to_dependencies,
                        install_order,
                    )
                )
