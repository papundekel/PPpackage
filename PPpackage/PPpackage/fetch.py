from asyncio import TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Mapping, MutableMapping, MutableSet
from functools import partial
from itertools import islice
from pathlib import Path
from typing import Any

from frozendict import frozendict
from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage_utils.parse import (
    Dependency,
    FetchInput,
    FetchOutput,
    FetchOutputValue,
    PackageWithDependencies,
    model_dump,
    model_validate,
)
from PPpackage_utils.utils import asubprocess_communicate

from .sub import fetch as PP_fetch


async def fetch_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    input: FetchInput,
) -> FetchOutput:
    process = create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    input_json_bytes = model_dump(debug, input)

    output_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s fetch.",
        input_json_bytes,
    )

    return model_validate(debug, FetchOutput, output_json_bytes)


async def fetch_manager(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    manager: str,
    cache_path: Path,
    input: FetchInput,
) -> FetchOutput:
    if manager == "PP":
        fetcher = partial(
            PP_fetch, runner_path=runner_path, runner_workdir_path=runner_workdir_path
        )
    else:
        fetcher = partial(fetch_external_manager, manager=manager)

    output = await fetcher(
        debug=debug,
        cache_path=cache_path,
        input=input,
    )

    return output


async def fetch(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    graph: MultiDiGraph,
    meta_options: Mapping[str, Mapping[str, Any] | None],
) -> Mapping[str, Mapping[str, FetchOutputValue]]:
    outputs: MutableMapping[str, MutableMapping[str, FetchOutputValue]] = {}

    reversed_graph = graph.reverse(copy=False)

    for generation in topological_generations(reversed_graph):
        manager_product_infos: MutableMapping[str, MutableMapping[str, Any]] = {}
        manager_packages: MutableMapping[str, MutableSet[PackageWithDependencies]] = {}
        for manager, name in generation:
            version = graph.nodes[(manager, name)]["version"]

            node_dependencies = list(
                islice(dfs_preorder_nodes(graph, source=(manager, name)), 1, None)
            )

            dependencies = set()
            for dependency_manager, dependency_name in node_dependencies:
                dependencies.add(
                    Dependency(manager=dependency_manager, name=dependency_name)
                )

                product_infos = manager_product_infos.setdefault(dependency_manager, {})

                if dependency_name not in product_infos:
                    product_infos[dependency_name] = outputs[dependency_manager][
                        dependency_name
                    ].product_info

            manager_packages.setdefault(manager, set()).add(
                PackageWithDependencies(
                    name=name,
                    version=version,
                    dependencies=dependencies,
                )
            )

        inputs = {
            manager: FetchInput(
                options=meta_options.get(manager),
                packages=packages,
                product_infos=manager_product_infos,
            )
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
                        input,
                    )
                )
                for manager, input in inputs.items()
            }

        for manager, task in manager_tasks.items():
            for package, value in task.result().root.items():
                outputs.setdefault(manager, {})[package] = value

    return outputs
