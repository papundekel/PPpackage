from ast import Mult
from asyncio import TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Iterable, Mapping, MutableMapping
from curses import meta
from functools import partial
from itertools import islice
from pathlib import Path
from sys import stderr
from tkinter import X
from typing import Any

from networkx import MultiDiGraph, dfs_preorder_nodes, topological_generations
from PPpackage_utils.parse import (
    FetchInput,
    FetchInputPackageValue,
    FetchOutput,
    FetchOutputValue,
)
from PPpackage_utils.utils import asubprocess_communicate, json_dumps, json_loads

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

    indent = 4 if debug else None

    input_json = json_dumps(input.model_dump(), indent=indent)

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s fetch:", file=stderr)
        print(input_json, file=stderr)

    input_json_bytes = input_json.encode("ascii")

    output_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s fetch.",
        input_json_bytes,
    )

    output_json = output_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}'s fetch:", file=stderr)
        print(output_json, file=stderr)

    output = FetchOutput.model_validate(json_loads(output_json))

    return output


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
        print(f"GENERATION: {generation}", file=stderr)

        manager_product_infos: MutableMapping[str, MutableMapping[str, Any]] = {}
        manager_packages: MutableMapping[
            str, MutableMapping[str, FetchInputPackageValue]
        ] = {}
        for manager, package in generation:
            version = graph.nodes[(manager, package)]["version"]

            dependencies = list(
                islice(dfs_preorder_nodes(graph, source=(manager, package)), 1, None)
            )

            value_dependencies = {}
            for dependency_manager, dependency in dependencies:
                value_dependencies.setdefault(dependency_manager, set()).add(dependency)

                product_infos = manager_product_infos.setdefault(dependency_manager, {})

                if dependency not in product_infos:
                    product_infos[dependency] = outputs[dependency_manager][
                        dependency
                    ].product_info

            value = FetchInputPackageValue(
                version=version, dependencies=value_dependencies
            )

            manager_packages.setdefault(manager, {})[package] = value

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
