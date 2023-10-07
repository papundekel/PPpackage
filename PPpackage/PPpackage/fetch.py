from asyncio import TaskGroup
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Iterable, Mapping
from functools import partial
from json import dumps as json_dumps
from json import loads as json_loads
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage_utils.utils import SetEncoder, asubprocess_communicate

from .generators import builtin as builtin_generators
from .sub import fetch as PP_fetch


async def fetch_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    process = create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        str(generators_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    indent = 4 if debug else None

    fetch_input_json = json_dumps(
        {
            "lockfile": versions,
            "options": options,
            "generators": generators - builtin_generators.keys(),
        },
        cls=SetEncoder,
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
    manager: str,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    if manager == "PP":
        fetcher = PP_fetch
    else:
        fetcher = partial(fetch_external_manager, manager=manager)

    product_ids = await fetcher(
        debug=debug,
        cache_path=cache_path,
        versions=versions,
        options=options,
        generators=generators,
        generators_path=generators_path,
    )

    return product_ids


async def fetch(
    debug: bool,
    cache_path: Path,
    meta_versions: Mapping[str, Mapping[str, str]],
    meta_options: Mapping[str, Any],
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, Mapping[str, str]]:
    async with TaskGroup() as group:
        meta_product_ids_tasks = {
            manager: group.create_task(
                fetch_manager(
                    debug,
                    manager,
                    cache_path,
                    versions,
                    meta_options.get(manager),
                    generators,
                    generators_path,
                )
            )
            for manager, versions in meta_versions.items()
        }

    meta_product_ids = {
        manager: product_ids_task.result()
        for manager, product_ids_task in meta_product_ids_tasks.items()
    }

    for generator in generators & builtin_generators.keys():
        builtin_generators[generator](generators_path, meta_versions, meta_product_ids)

    return meta_product_ids
