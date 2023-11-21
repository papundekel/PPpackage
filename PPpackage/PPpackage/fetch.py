from asyncio import Event, StreamReader, StreamWriter, TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import (
    Callable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
)
from contextlib import contextmanager
from functools import partial
from itertools import islice
from pathlib import Path
from re import S
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage_utils.parse import (
    Dependency,
    FetchOutputValue,
    ManagerAndName,
    Options,
    Package,
    dump_loop,
    dump_many,
    dump_many_end,
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
    receiver: Callable[[FetchOutputValue], None],
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


class Synchronization:
    receive_event = Event()
    package_name: str

    send_event = Event()

    end = False


@contextmanager
def set_event(event: Event):
    try:
        yield
    finally:
        event.set()


async def wait_and_clear(event: Event):
    await event.wait()
    event.clear()


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

    # while True:
    #     with set_event(Synchronization.send_event):
    #         await wait_and_clear(Synchronization.receive_event)

    #         if Synchronization.end:
    #             break

    #         package_name = Synchronization.package_name

    #         print(f"build response: {package_name}", file=stderr)

    writer.close()


async def receive(
    debug: bool,
    reader: StreamReader,
    receiver: Callable[[FetchOutputValue], None],
) -> None:
    # async for package_name in load_many(debug, reader, str):
    #     Synchronization.package_name = package_name
    #     Synchronization.receive_event.set()

    #     await wait_and_clear(Synchronization.send_event)

    # Synchronization.end = True
    # Synchronization.receive_event.set()

    # await Synchronization.send_event.wait()

    async for value in load_many(debug, reader, FetchOutputValue):
        receiver(value)


def receiver(
    manager: str,
    nodes: Mapping[tuple[str, str], MutableMapping[str, Any]],
    product: FetchOutputValue,
) -> None:
    node = nodes[(manager, product.name)]
    node["product_id"] = product.product_id
    node["product_info"] = product.product_info


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
