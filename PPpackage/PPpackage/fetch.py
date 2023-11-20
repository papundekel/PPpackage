from asyncio import TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Iterable, Mapping, MutableMapping, MutableSet
from functools import partial
from itertools import islice
from pathlib import Path
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage_utils.parse import (
    Dependency,
    FetchOutput,
    ManagerAndName,
    Options,
    PackageWithDependencies,
    model_dump_stream,
    model_validate_stream,
    models_dump_stream,
)
from PPpackage_utils.utils import asubprocess_wait

from .sub import fetch as PP_fetch


async def fetch_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    options: Options,
    packages: Iterable[PackageWithDependencies],
) -> FetchOutput:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    assert process.stdin is not None
    assert process.stdout is not None

    model_dump_stream(debug, process.stdin, options)
    models_dump_stream(debug, process.stdin, packages)

    output = model_validate_stream(debug, process.stdout, FetchOutput)

    await process.stdin.drain()
    await asubprocess_wait(process, f"Error in {manager}'s fetch.")

    return await output


async def fetch_manager(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    manager: str,
    cache_path: Path,
    options: Options,
    packages: Iterable[PackageWithDependencies],
) -> FetchOutput:
    if manager == "PP":
        fetcher = partial(
            PP_fetch, runner_path=runner_path, runner_workdir_path=runner_workdir_path
        )
    else:
        fetcher = partial(fetch_external_manager, manager=manager)

    output = await fetcher(
        debug=debug, cache_path=cache_path, options=options, packages=packages
    )

    return output


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
        manager_packages: MutableMapping[str, MutableSet[PackageWithDependencies]] = {}

        for manager, name in generation:
            version = graph.nodes[(manager, name)]["version"]

            dependencies = create_dependencies(sent_product_infos, graph, manager, name)

            manager_packages.setdefault(manager, set()).add(
                PackageWithDependencies(
                    name=name, version=version, dependencies=dependencies
                )
            )

        inputs = {
            manager: (meta_options.get(manager), packages)
            for manager, packages in manager_packages.items()
        }

        async with TaskGroup() as group:
            manager_tasks = {
                manager: group.create_task(
                    fetch_manager(
                        debug,
                        runner_path,
                        runner_workdir_path,
                        manager,
                        cache_path,
                        options,
                        packages,
                    )
                )
                for manager, (options, packages) in inputs.items()
            }

        for manager, task in manager_tasks.items():
            for package in task.result():
                node = graph.nodes[(manager, package.name)]
                node["product_id"] = package.product_id
                node["product_info"] = package.product_info
