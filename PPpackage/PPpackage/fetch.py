from asyncio import TaskGroup
from collections.abc import AsyncIterable, Iterable, Mapping, MutableMapping, MutableSet
from itertools import chain, islice
from pathlib import Path
from sys import stderr
from typing import Any

from asyncstdlib import list as async_list
from networkx import (
    MultiDiGraph,
    dfs_preorder_nodes,
    subgraph_view,
    topological_generations,
)
from PPpackage_submanager.schemes import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    ProductIDAndInfo,
)
from PPpackage_utils.utils import TemporaryDirectory

from .generate import generate
from .install import install
from .resolve import resolve
from .schemes import NodeData
from .submanager import Submanager
from .topology import create_install_topology
from .utils import NodeData, SubmanagerCommandFailure


async def fetch_install(
    workdir_path: Path,
    submanagers: Mapping[str, Submanager],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
    extra_requirements_iterable: Iterable[tuple[str, Any]],
    resolve_iteration_limit,
):
    stderr.write("Creating build context...\n")

    dependency_dict = {
        manager_and_name: data for manager_and_name, data in dependencies
    }

    extra_requirements = dict[str, MutableSet[Any]]()

    for submanager_name, requirement in extra_requirements_iterable:
        extra_requirements.setdefault(submanager_name, set()).add(requirement)

    locks = dict[str, MutableMapping[str, str]]()
    for dependency, data in dependency_dict.items():
        locks.setdefault(dependency.manager, {})[dependency.name] = data["version"]

    extra_graph = await resolve(
        submanagers, resolve_iteration_limit, extra_requirements, locks, {}
    )

    for dependency, data in dependency_dict.items():
        extra_graph_node = extra_graph.nodes.get(dependency)

        if extra_graph_node is None:
            continue

        if extra_graph_node["version"] != data["version"]:
            raise SubmanagerCommandFailure(
                f"Version mismatch for {dependency}: {extra_graph_node['version']} != {data['version']}"
            )

        extra_graph_node["product_id"] = data["product_id"]
        extra_graph_node["product_info"] = data["product_info"]

    extra_subgraph: MultiDiGraph = subgraph_view(
        extra_graph, filter_node=lambda node: node not in dependency_dict
    )  # type: ignore

    await fetch(
        workdir_path,
        submanagers,
        {},  # TODO
        extra_graph,
        extra_subgraph,
        resolve_iteration_limit,
    )

    dependency_install_order = (
        (node, data) for node, data in install_order if node in dependency_dict
    )
    extra_install_order = create_install_topology(extra_graph)

    await install(
        submanagers,
        chain(dependency_install_order, extra_install_order),
        destination_path,
    )

    stderr.write("Build context created.\n")


async def fetch_generate(
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    async_generators: AsyncIterable[str],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
):
    stderr.write("Creating generators for the build context...\n")

    generators = await async_list(async_generators)

    await generate(
        submanagers, generators, dependencies, meta_options, destination_path
    )

    stderr.write("Build context generators created.\n")


async def fetch_install_generate(
    workdir_path: Path,
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    async_extra_requirements: AsyncIterable[tuple[str, Any]],
    async_generators: AsyncIterable[str],
    installation_path: Path,
    generators_path: Path,
    resolve_iteration_limit: int,
):
    # need to iterate requirements before generators
    extra_requirements = await async_list(async_extra_requirements)

    async with TaskGroup() as group:
        group.create_task(
            fetch_install(
                workdir_path,
                submanagers,
                install_order,
                dependencies,
                installation_path,
                extra_requirements,
                resolve_iteration_limit,
            )
        )
        group.create_task(
            fetch_generate(
                submanagers,
                meta_options,
                async_generators,
                dependencies,
                generators_path,
            )
        )


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
    resolve_iteration_limit: int,
):
    submanager = submanagers[submanager_name]
    options = meta_options.get(submanager.name)

    async with submanager.fetch(
        options, package, dependencies, None, None
    ) as result_first:
        if isinstance(result_first, ProductIDAndInfo):
            id_and_info = result_first
        else:
            async_requirements = result_first.requirements
            async_generators = result_first.generators

            meta_dependencies = packages_to_dependencies[
                ManagerAndName(submanager.name, package.name)
            ]

            with (
                TemporaryDirectory(workdir_path) as installation_path,
                TemporaryDirectory(workdir_path) as generators_path,
            ):
                await fetch_install_generate(
                    workdir_path,
                    submanagers,
                    meta_options,
                    install_order,
                    meta_dependencies,
                    async_requirements,
                    async_generators,
                    installation_path,
                    generators_path,
                    resolve_iteration_limit,
                )

                stderr.write(f"Fetching again with build context...\n")

                async with submanager.fetch(
                    options, package, dependencies, installation_path, generators_path
                ) as result_second:
                    if isinstance(result_second, ProductIDAndInfo):
                        id_and_info = result_second
                    else:
                        raise SubmanagerCommandFailure("Fetch failed.")

                stderr.write(f"Fetching done.\n")

    node = nodes[ManagerAndName(submanager.name, package.name)]
    node["product_id"] = id_and_info.product_id
    node["product_info"] = id_and_info.product_info

    stderr.write(f"\t{submanager.name}: {package.name} -> {id_and_info.product_id}\n")


async def fetch(
    workdir_path: Path,
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    graph: MultiDiGraph,
    subgraph: MultiDiGraph,
    resolve_iteration_limit: int,
):
    stderr.write("Fetching packages...\n")

    install_order = list(create_install_topology(graph))
    generations = topological_generations(subgraph.reverse(copy=False))

    packages_to_dependencies: MutableMapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ] = {}

    for generation in generations:
        async with TaskGroup() as group:
            for node in generation:
                node_dependencies = list(graph_successors(graph, node))

                dependencies = create_dependencies(node_dependencies)

                packages_to_dependencies[node] = node_dependencies

                group.create_task(
                    fetch_manager(
                        workdir_path,
                        submanagers,
                        node.manager,
                        meta_options,
                        Package(name=node.name, version=graph.nodes[node]["version"]),
                        dependencies,
                        graph.nodes,
                        packages_to_dependencies,
                        install_order,
                        resolve_iteration_limit,
                    )
                )

    stderr.write("Fetching done.\n")

    return install_order
