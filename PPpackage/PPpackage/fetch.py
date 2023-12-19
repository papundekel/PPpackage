from asyncio import StreamReader, StreamWriter, TaskGroup
from collections.abc import Iterable, Mapping, MutableMapping
from itertools import islice
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes
from PPpackage_utils.parse import (
    Dependency,
    ManagerAndName,
    Options,
    Package,
    PackageIDAndInfo,
    dump_bytes_chunked,
    dump_many,
    dump_one,
    load_many,
    load_one,
)
from PPpackage_utils.utils import SubmanagerCommand, create_empty_tar

from PPpackage.generate import generate
from PPpackage.install import install

from .utils import Connections, NodeData, SubmanagerCommandFailure, load_success


async def build_install(
    debug: bool,
    connections: Connections,
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

    dependency_install_order = [
        (node, data) for node, data in install_order if node in dependency_set
    ]

    return await install(
        debug, connections, create_empty_tar(), dependency_install_order
    )


async def send(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    manager: str,
    options: Options,
    package: Package,
    dependencies: Iterable[Dependency],
    installation: memoryview | None,
    generators: memoryview | None,
):
    await dump_one(debug, writer, options)
    await dump_one(debug, writer, package)

    installation_present = installation is not None
    await dump_one(debug, writer, installation_present)
    if installation_present:
        await dump_bytes_chunked(debug, writer, installation)

    generators_present = generators is not None
    await dump_one(debug, writer, generators_present)
    if generators_present:
        await dump_bytes_chunked(debug, writer, generators)

    await dump_many(debug, writer, dependencies)

    await load_success(
        debug, reader, f"{manager} failed to fetch package {package.name}."
    )


async def fetch_manager(
    debug: bool,
    connections: Connections,
    manager: str,
    meta_options: Mapping[str, Options],
    package: Package,
    dependencies: Iterable[Dependency],
    nodes: Mapping[ManagerAndName, NodeData],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
):
    async with connections.connect(debug, manager, SubmanagerCommand.FETCH) as (
        reader,
        writer,
    ):
        options = meta_options.get(manager)
        await send(
            debug, reader, writer, manager, options, package, dependencies, None, None
        )

        no_build = await load_one(debug, reader, bool)

        if not no_build:
            async with TaskGroup() as group:
                dependencieds = packages_to_dependencies[
                    ManagerAndName(manager, package.name)
                ]

                task_install = group.create_task(
                    build_install(debug, connections, install_order, dependencieds)
                )

                generators = [
                    generator async for generator in load_many(debug, reader, str)
                ]
                task_generate = group.create_task(
                    generate(
                        debug, connections, generators, dependencieds, meta_options
                    )
                )

            installation = task_install.result()
            generators = task_generate.result()

            async with connections.connect(debug, manager, SubmanagerCommand.FETCH) as (
                r2,
                w2,
            ):
                await send(
                    debug,
                    r2,
                    w2,
                    manager,
                    options,
                    package,
                    dependencies,
                    installation,
                    generators,
                )

                no_build = await load_one(debug, r2, bool)

                if not no_build:
                    raise SubmanagerCommandFailure(
                        f"{manager} failed to build package {package.name}."
                    )

                id_and_info = await load_one(debug, r2, PackageIDAndInfo)
        else:
            id_and_info = await load_one(debug, reader, PackageIDAndInfo)

    node = nodes[ManagerAndName(manager, package.name)]
    node["product_id"] = id_and_info.product_id
    node["product_info"] = id_and_info.product_info

    stderr.write(f"{manager}: {package.name} -> {id_and_info.product_id}\n")


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
    debug: bool,
    connections: Connections,
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

                group.create_task(
                    fetch_manager(
                        debug,
                        connections,
                        node.manager,
                        meta_options,
                        Package(name=node.name, version=data["version"]),
                        dependencies,
                        graph.nodes,
                        packages_to_dependencies,
                        install_order,
                    )
                )
