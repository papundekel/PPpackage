from ast import Mult
from asyncio import TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Iterable, Mapping
from curses import meta
from functools import partial
from pathlib import Path
from sys import stderr
from typing import Any

from networkx import MultiDiGraph, topological_generations
from networkx.drawing.nx_pydot import to_pydot
from PPpackage_utils.utils import asubprocess_communicate, json_dumps, json_loads

from .sub import fetch as PP_fetch


async def fetch_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
) -> Mapping[str, str]:
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

    fetch_input_json = json_dumps(
        {
            "lockfile": versions,
            "options": options,
        },
        indent=indent,
    )

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s fetch:", file=stderr)
        print(fetch_input_json, file=stderr)

    fetch_input_json_bytes = fetch_input_json.encode("ascii")

    product_ids_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s fetch.",
        fetch_input_json_bytes,
    )

    product_ids_json = product_ids_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}'s fetch:", file=stderr)
        print(product_ids_json, file=stderr)

    product_ids = json_loads(product_ids_json)

    return product_ids


async def fetch_manager(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    manager: str,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
) -> Mapping[str, str]:
    if manager == "PP":
        fetcher = partial(
            PP_fetch, runner_path=runner_path, runner_workdir_path=runner_workdir_path
        )
    else:
        fetcher = partial(fetch_external_manager, manager=manager)

    product_ids = await fetcher(
        debug=debug,
        cache_path=cache_path,
        versions=versions,
        options=options,
    )

    return product_ids


async def fetch(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    graph: MultiDiGraph,
    meta_options: Mapping[str, Any],
) -> Mapping[str, Mapping[str, str]]:
    meta_product_ids = {}

    reversed_graph = graph.reverse(copy=False)

    for generation in topological_generations(reversed_graph):
        versions = {}
        for manager, package in generation:
            versions.setdefault(manager, {})[package] = graph.nodes[(manager, package)][
                "version"
            ]

        async with TaskGroup() as group:
            manager_tasks = {
                manager: group.create_task(
                    fetch_manager(
                        debug,
                        runner_path,
                        runner_workdir_path,
                        manager,
                        cache_path,
                        versions,
                        meta_options.get(manager),
                    )
                )
                for manager, versions in versions.items()
            }

        for manager, task in manager_tasks.items():
            for package, product_id in task.result().items():
                meta_product_ids.setdefault(manager, {})[package] = product_id

    return meta_product_ids
