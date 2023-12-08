from asyncio import Queue as BaseQueue
from asyncio import StreamReader, StreamWriter, TaskGroup, as_completed
from collections.abc import (
    AsyncIterable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
)
from contextlib import asynccontextmanager
from itertools import islice
from sys import stderr
from typing import Any, TypeVar

from networkx import MultiDiGraph, dfs_preorder_nodes
from PPpackage_utils.parse import (
    BuildResult,
    Dependency,
    ManagerAndName,
    Options,
    Package,
    PackageIDAndInfo,
    dump_loop,
    dump_loop_end,
    dump_many,
    dump_one,
    load_many,
    load_one,
)
from PPpackage_utils.utils import (
    Queue,
    SubmanagerCommand,
    queue_iterate,
    queue_put_loop,
)

from .utils import NodeData


class Synchronization:
    package_names = Queue[str]()


async def process_build_root(
    manager: str,
    package_name: str,
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    return True, bytes()  # TODO


async def process_build_generate(
    manager: str,
    package_name: str,
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    return False, bytes()  # TODO


async def process_build(
    debug: bool,
    writer: StreamWriter,
    manager: str,
    package_name: str,
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    for f in as_completed(
        [
            process_build_root(manager, package_name, dependencies),
            process_build_generate(manager, package_name, dependencies),
        ]
    ):
        is_root, directory = await f

        await dump_one(
            debug,
            writer,
            BuildResult(
                name=package_name, is_root=is_root, directory=directory.decode("ascii")
            ),
            loop=True,
        )


async def send(
    debug: bool,
    writer: StreamWriter,
    manager: str,
    options: Options,
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
) -> None:
    await dump_one(debug, writer, SubmanagerCommand.FETCH)

    await dump_one(debug, writer, options)

    async for package, dependencies in dump_loop(debug, writer, packages):
        await dump_one(debug, writer, package)
        await dump_many(debug, writer, dependencies)

    async with TaskGroup() as group:
        async for package_name in queue_iterate(Synchronization.package_names):
            dependencies = packages_to_dependencies[
                ManagerAndName(name=package_name, manager=manager)
            ]

            group.create_task(
                process_build(debug, writer, manager, package_name, dependencies)
            )

    await dump_loop_end(debug, writer)


async def receive(
    debug: bool,
    reader: StreamReader,
    manager: str,
    nodes: Mapping[ManagerAndName, NodeData],
    package_names: Iterable[str],
) -> bool:
    packages_unfetched = set(package_names)
    end = False

    async for package_id_and_info in load_many(debug, reader, PackageIDAndInfo):
        if end:
            return False

        package_name = package_id_and_info.name
        id_and_info = package_id_and_info.id_and_info

        if id_and_info is not None:
            node = nodes[ManagerAndName(manager, package_name)]

            if package_name not in packages_unfetched:
                return False

            node["product_id"] = id_and_info.product_id
            node["product_info"] = id_and_info.product_info

            packages_unfetched.remove(package_name)

            if len(packages_unfetched) == 0:
                await Synchronization.package_names.put(None)
                end = True
        else:
            await Synchronization.package_names.put(package_name)

    success = await load_one(debug, reader, bool)

    return success


def log(
    manager: str,
    success: bool,
    packages: Iterable[tuple[Package, Any]],
    nodes: Mapping[ManagerAndName, NodeData],
):
    stderr.write(f"{manager}:\n")
    if success:
        for package, _ in sorted(packages, key=lambda p: p[0].name):
            product_id = nodes[ManagerAndName(manager, package.name)]["product_id"]
            stderr.write(f"\t{package.name} -> {product_id}\n")
    else:
        stderr.write("\tFailed.\n")


async def fetch_manager(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    manager: str,
    options: Options,
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    nodes: Mapping[ManagerAndName, NodeData],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
) -> bool:
    reader, writer = connections[manager]

    async with TaskGroup() as group:
        group.create_task(
            send(
                debug,
                writer,
                manager,
                options,
                packages,
                packages_to_dependencies,
            )
        )
        success_task = group.create_task(
            receive(
                debug, reader, manager, nodes, (package.name for package, _ in packages)
            )
        )

    success = success_task.result()

    log(manager, success, packages, nodes)

    return success


def create_dependencies(
    sent_product_infos: MutableSet[ManagerAndName],
    node_dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    dependencies = []

    for manager_and_name, data in node_dependencies:
        product_info = (
            None if manager_and_name in sent_product_infos else data["product_info"]
        )

        dependency = Dependency(
            manager=manager_and_name.manager,
            name=manager_and_name.name,
            product_info=product_info,
        )

        dependencies.append(dependency)
        sent_product_infos.add(super(Dependency, dependency))

    return dependencies


def graph_predecessors(
    graph: MultiDiGraph, node: Any
) -> Iterable[tuple[ManagerAndName, NodeData]]:
    for node in islice(dfs_preorder_nodes(graph, source=node), 1, None):
        yield node, graph.nodes[node]


async def fetch(
    debug: bool,
    connections: Mapping[str, tuple[StreamReader, StreamWriter]],
    meta_options: Mapping[str, Mapping[str, Any] | None],
    graph: MultiDiGraph,
    generations: Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]],
) -> bool:
    stderr.write("Fetching packages...\n")

    packages_to_dependencies: MutableMapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ] = {}

    for manager_to_generation in generations:
        sent_product_infos: MutableSet[ManagerAndName] = set()
        manager_packages: MutableMapping[
            str, MutableSequence[tuple[Package, Iterable[Dependency]]]
        ] = {}

        for manager, generation in manager_to_generation.items():
            for package_name, data in generation:
                manager_and_name = ManagerAndName(manager, package_name)

                node_dependencies = list(graph_predecessors(graph, manager_and_name))

                dependencies = create_dependencies(
                    sent_product_infos, node_dependencies
                )

                packages_to_dependencies[manager_and_name] = node_dependencies

                manager_packages.setdefault(manager, []).append(
                    (Package(name=package_name, version=data["version"]), dependencies)
                )

        async with TaskGroup() as group:
            success_tasks = []

            for manager, packages in manager_packages.items():
                success_tasks.append(
                    group.create_task(
                        fetch_manager(
                            debug,
                            connections,
                            manager,
                            meta_options.get(manager),
                            packages,
                            graph.nodes,
                            packages_to_dependencies,
                        )
                    )
                )

        if any(not success_task.result() for success_task in success_tasks):
            stderr.write("Fetching failed. Aborting.\n")
            return False

    return True
