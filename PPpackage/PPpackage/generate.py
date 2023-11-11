from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from sys import stderr
from typing import Any, Iterable

from PPpackage_utils.parse import json_dumps
from PPpackage_utils.utils import asubprocess_communicate

from .generators import builtin as builtin_generators
from .sub import generate as PP_generate
from .utils import merge_lockfiles


async def generate_external_manager(
    debug: bool,
    cache_path: Path,
    manager: str,
    generators: Iterable[str],
    generators_path: Path,
    options: Mapping[str, Any] | None,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    process = create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "generate",
        str(cache_path),
        str(generators_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    packages = merge_lockfiles(versions, product_ids)

    generate_input_json = json_dumps(
        {"generators": generators, "packages": packages, "options": options},
        indent=4 if debug else None,
    )

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s generate:", file=stderr)
        print(generate_input_json, file=stderr)

    generate_input_json_bytes = generate_input_json.encode("ascii")

    await asubprocess_communicate(
        await process,
        f"Error in {manager}'s generate.",
        generate_input_json_bytes,
    )


async def generate_manager(
    debug: bool,
    cache_path: Path,
    manager: str,
    generators: Iterable[str],
    generators_path: Path,
    options: Mapping[str, Any] | None,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    if manager == "PP":
        generate = PP_generate
    else:
        generate = partial(generate_external_manager, manager=manager)

    await generate(
        debug=debug,
        cache_path=cache_path,
        generators=generators,
        generators_path=generators_path,
        options=options,
        versions=versions,
        product_ids=product_ids,
    )


async def generate(
    debug: bool,
    cache_path: Path,
    generators: Iterable[str],
    generators_path: Path,
    meta_options: Mapping[str, Mapping[str, Any] | None],
    meta_versions: Mapping[str, Mapping[str, str]],
    meta_product_ids: Mapping[str, Mapping[str, str]],
):
    async with TaskGroup() as group:
        for manager, versions in meta_versions.items():
            group.create_task(
                generate_manager(
                    debug,
                    cache_path,
                    manager,
                    generators - builtin_generators.keys(),
                    generators_path,
                    meta_options.get(manager),
                    versions,
                    meta_product_ids[manager],
                )
            )

        for generator in generators & builtin_generators.keys():
            builtin_generators[generator](
                generators_path, meta_versions, meta_product_ids
            )
