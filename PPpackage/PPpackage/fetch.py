from asyncio import Event
from asyncio import Queue as BaseQueue
from asyncio import StreamReader, StreamWriter, TaskGroup, as_completed
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import (
    AsyncIterable,
    Callable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
)
from contextlib import asynccontextmanager
from functools import partial
from itertools import islice
from pathlib import Path
from sys import stderr
from typing import Any, TypeVar

from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage_utils.parse import (
    BuildResult,
    Dependency,
    IDAndInfo,
    ManagerAndName,
    Options,
    Package,
    PackageIDAndInfo,
    dump_loop,
    dump_loop_end,
    dump_many,
    dump_one,
    load_many,
)
from PPpackage_utils.utils import asubprocess_wait, debug_redirect_stderr

from .sub import fetch as PP_fetch


async def fetch_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    options: Options,
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    receiver: Callable[[str, IDAndInfo], None],
) -> None:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=debug_redirect_stderr(debug),
    )

    assert process.stdin is not None
    assert process.stdout is not None

    async with TaskGroup() as group:
        group.create_task(send(debug, process.stdin, options, packages))
        group.create_task(receive(debug, process.stdout, receiver))

    await asubprocess_wait(process, f"Error in {manager}'s fetch.")


T = TypeVar("T")

Queue = BaseQueue[T | None]


async def queue_iterate(queue: Queue[T]) -> AsyncIterable[T]:
    while True:
        value = await queue.get()

        if value is None:
            break

        yield value


@asynccontextmanager
async def queue_put_loop(queue: Queue[T]):
    try:
        yield
    finally:
        queue.put_nowait(None)


class Synchronization:
    package_names = Queue[str]()


async def process_build_root(package_name: str):
    return True, bytes()  # TODO


async def process_build_generate(package_name: str):
    return False, bytes()  # TODO


async def process_build(debug: bool, writer: StreamWriter, package_name: str):
    print(f"build response: {package_name}", file=stderr)

    for f in as_completed(
        [process_build_root(package_name), process_build_generate(package_name)]
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
    options: Options,
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
) -> None:
    await dump_one(debug, writer, options)

    async for package, dependencies in dump_loop(debug, writer, packages):
        await dump_one(debug, writer, package)
        await dump_many(debug, writer, dependencies)

    async with TaskGroup() as group:
        async for package_name in queue_iterate(Synchronization.package_names):
            group.create_task(process_build(debug, writer, package_name))

    await dump_loop_end(debug, writer)

    writer.close()


async def receive(
    debug: bool,
    reader: StreamReader,
    receiver: Callable[[str, IDAndInfo], None],
) -> None:
    async with queue_put_loop(Synchronization.package_names):
        async for package_id_and_info in load_many(debug, reader, PackageIDAndInfo):
            package_name = package_id_and_info.name
            id_and_info = package_id_and_info.id_and_info

            if id_and_info is not None:
                receiver(package_name, id_and_info)
            else:
                Synchronization.package_names.put_nowait(package_name)


def receiver(
    manager: str,
    nodes: Mapping[tuple[str, str], MutableMapping[str, Any]],
    package_name: str,
    id_and_info: IDAndInfo,
) -> None:
    node = nodes[(manager, package_name)]
    node["product_id"] = id_and_info.product_id
    node["product_info"] = id_and_info.product_info


async def fetch_manager(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    manager: str,
    cache_path: Path,
    options: Options,
    packages: Iterable[tuple[Package, Iterable[Dependency]]],
    nodes: Mapping[tuple[str, str], MutableMapping[str, Any]],
) -> None:
    if manager == "PP":
        fetcher = partial(
            PP_fetch, runner_path=runner_path, runner_workdir_path=runner_workdir_path
        )
    else:
        fetcher = partial(fetch_external_manager, manager=manager)

    await fetcher(
        debug=debug,
        cache_path=cache_path,
        options=options,
        packages=packages,
        receiver=partial(receiver, manager, nodes),
    )


def create_dependencies(
    sent_product_infos: MutableSet[ManagerAndName],
    graph: MultiDiGraph,
    manager: str,
    package_name: str,
):
    dependencies = []

    node_dependencies = list(
        islice(dfs_preorder_nodes(graph, source=(manager, package_name)), 1, None)
    )

    for dependency_manager, dependency_name in node_dependencies:
        product_info = (
            None
            if ManagerAndName(name=dependency_name, manager=dependency_manager)
            in sent_product_infos
            else graph.nodes[(dependency_manager, dependency_name)]["product_info"]
        )

        dependency = Dependency(
            manager=dependency_manager, name=dependency_name, product_info=product_info
        )

        dependencies.append(dependency)
        sent_product_infos.add(super(Dependency, dependency))

    return dependencies


async def fetch(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    meta_options: Mapping[str, Mapping[str, Any] | None],
    graph: MultiDiGraph,
) -> None:
    reversed_graph = graph.reverse(copy=False)

    for generation in topological_generations(reversed_graph):
        sent_product_infos: MutableSet[ManagerAndName] = set()
        manager_packages: MutableMapping[
            str, MutableSequence[tuple[Package, Iterable[Dependency]]]
        ] = {}

        for manager, name in generation:
            version = graph.nodes[(manager, name)]["version"]

            dependencies = create_dependencies(sent_product_infos, graph, manager, name)

            manager_packages.setdefault(manager, []).append(
                (Package(name=name, version=version), dependencies)
            )

        async with TaskGroup() as group:
            for manager, packages in manager_packages.items():
                group.create_task(
                    fetch_manager(
                        debug,
                        runner_path,
                        runner_workdir_path,
                        manager,
                        cache_path,
                        meta_options.get(manager),
                        packages,
                        graph.nodes,
                    )
                )
