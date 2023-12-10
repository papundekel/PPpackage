from asyncio import Lock, StreamReader, StreamWriter, TaskGroup, as_completed
from collections.abc import (
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)
from itertools import islice
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes
from PPpackage_utils.parse import (
    BuildResult,
    Dependency,
    ManagerAndName,
    Options,
    Package,
    PackageIDAndInfo,
    dump_bytes_chunked,
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
    create_empty_tar,
    queue_iterate,
)

from PPpackage.generate import generate
from PPpackage.install import install

from .utils import Connections, NodeData, SubmanagerCommandFailure


async def process_build_root(
    debug: bool,
    connections: Connections,
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
):
    connections = connections.duplicate()

    dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

    dependency_generations = [
        {
            manager: [
                (package, data)
                for package, data in packages
                if ManagerAndName(manager, package) in dependency_set
            ]
            for manager, packages in generation.items()
        }
        for generation in generations
    ]

    async with connections.communicate(debug):
        return True, await install(
            debug, connections, create_empty_tar(), dependency_generations
        )


async def process_build_generate(
    debug: bool,
    connections: Connections,
    meta_options: Mapping[str, Options],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    generators: Iterable[str],
):
    connections = connections.duplicate()

    async with connections.communicate(debug):
        return False, await generate(
            debug, connections, False, generators, dependencies, meta_options
        )


async def process_build(
    debug: bool,
    lock: Lock,
    connections: Connections,
    writer: StreamWriter,
    meta_options: Mapping[str, Options],
    package_name: str,
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    generators: Iterable[str],
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
):
    for f in as_completed(
        [
            process_build_root(debug, connections, generations, dependencies),
            process_build_generate(
                debug, connections, meta_options, dependencies, generators
            ),
        ]
    ):
        is_root, directory = await f

        # the message must be sent atomically
        await lock.acquire()

        await dump_one(
            debug,
            writer,
            BuildResult(name=package_name, is_root=is_root),
            loop=True,
        )

        await dump_bytes_chunked(debug, writer, directory)

        lock.release()


BuildQueue = Queue[tuple[str, Iterable[str]]]


async def send(
    debug: bool,
    build_queue: BuildQueue,
    connections: Connections,
    writer: StreamWriter,
    manager: str,
    meta_options: Mapping[str, Options],
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
) -> None:
    await dump_one(debug, writer, SubmanagerCommand.FETCH)

    options = meta_options.get(manager)

    await dump_one(debug, writer, options)

    async for package, dependencies in dump_loop(debug, writer, packages):
        await dump_one(debug, writer, package)
        await dump_many(debug, writer, dependencies)

    build_lock = Lock()

    async with TaskGroup() as group:
        async for package_name, generators in queue_iterate(build_queue):
            dependencies = packages_to_dependencies[
                ManagerAndName(name=package_name, manager=manager)
            ]

            group.create_task(
                process_build(
                    debug,
                    build_lock,
                    connections,
                    writer,
                    meta_options,
                    package_name,
                    dependencies,
                    generators,
                    generations,
                )
            )

    await dump_loop_end(debug, writer)


def receive_check(end: bool, manager: str, package_name: str, packages_all: set):
    if end:
        raise SubmanagerCommandFailure(
            f"Too many packages received from {manager}. Got {package_name}."
        )

    if package_name not in packages_all:
        raise SubmanagerCommandFailure(
            f"Unrequested package received from {manager}: {package_name}."
        )


def receive_check_build(
    end: bool,
    manager: str,
    package_name: str,
    packages_all: set,
    packages_build_requested: set,
    packages_remaining: set,
):
    receive_check(end, manager, package_name, packages_all)

    if package_name in packages_build_requested:
        raise SubmanagerCommandFailure(
            f"Build of {package_name} already requested from {manager}."
        )

    if package_name not in packages_remaining:
        raise SubmanagerCommandFailure(
            f"{package_name} from {manager} was already built."
        )


async def receive(
    debug: bool,
    build_queue: BuildQueue,
    reader: StreamReader,
    manager: str,
    nodes: Mapping[ManagerAndName, NodeData],
    package_names: Iterable[str],
):
    packages_all = set(package_names)
    packages_remaining = packages_all.copy()
    packages_build_requested = set()
    end = False

    async for is_id_and_info in load_many(debug, reader, bool):
        if is_id_and_info:
            package_id_and_info = await load_one(debug, reader, PackageIDAndInfo)
            package_name = package_id_and_info.name

            receive_check(end, manager, package_name, packages_all)

            node = nodes[ManagerAndName(manager, package_name)]

            node["product_id"] = package_id_and_info.product_id
            node["product_info"] = package_id_and_info.product_info

            packages_remaining.remove(package_name)

            if len(packages_remaining) == 0:
                await build_queue.put(None)
                end = True
        else:
            package_name = await load_one(debug, reader, str)

            receive_check_build(
                end,
                manager,
                package_name,
                packages_all,
                packages_build_requested,
                packages_remaining,
            )

            generators = [
                generator async for generator in load_many(debug, reader, str)
            ]

            await build_queue.put((package_name, generators))

            packages_build_requested.add(package_name)

    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(f"{manager} failed to fetch packages.")


async def fetch_manager(
    debug: bool,
    connections: Connections,
    manager: str,
    meta_options: Mapping[str, Options],
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    nodes: Mapping[ManagerAndName, NodeData],
    packages_to_dependencies: Mapping[
        ManagerAndName, Iterable[tuple[ManagerAndName, NodeData]]
    ],
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
):
    reader, writer = await connections.connect(manager, strict=True)

    build_queue = BuildQueue()

    async with TaskGroup() as group:
        group.create_task(
            send(
                debug,
                build_queue,
                connections,
                writer,
                manager,
                meta_options,
                packages,
                packages_to_dependencies,
                generations,
            )
        )
        group.create_task(
            receive(
                debug,
                build_queue,
                reader,
                manager,
                nodes,
                (package.name for package, _ in packages),
            )
        )

    stderr.write(f"{manager}:\n")
    for package, _ in sorted(packages, key=lambda p: p[0].name):
        product_id = nodes[ManagerAndName(manager, package.name)]["product_id"]
        stderr.write(f"\t{package.name} -> {product_id}\n")


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
    connections: Connections,
    meta_options: Mapping[str, Mapping[str, Any] | None],
    graph: MultiDiGraph,
    generations: Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]],
):
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
            for manager, packages in manager_packages.items():
                group.create_task(
                    fetch_manager(
                        debug,
                        connections,
                        manager,
                        meta_options,
                        packages,
                        graph.nodes,
                        packages_to_dependencies,
                        generations,
                    )
                )
