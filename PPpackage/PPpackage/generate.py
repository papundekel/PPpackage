from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping, Set
from pathlib import Path
from typing import Any, Iterable

from PPpackage_utils.parse import Options, Product, dump_many, dump_one
from PPpackage_utils.utils import asubprocess_wait, debug_redirect_stderr

from .generators import builtin as builtin_generators


async def generate_manager(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    options: Options,
    products: Iterable[Product],
    generators: Set[str],
    manager: str,
) -> None:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "generate",
        str(cache_path),
        str(generators_path),
        stdin=PIPE,
        stdout=DEVNULL,
        stderr=debug_redirect_stderr(debug),
    )

    assert process.stdin is not None

    await dump_one(debug, process.stdin, options)
    await dump_many(debug, process.stdin, products)
    await dump_many(debug, process.stdin, generators)

    await asubprocess_wait(process, f"Error in {manager}'s generate.")


async def generate(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    generators: Iterable[str],
    meta_products: Mapping[str, Iterable[Product]],
    meta_options: Mapping[str, Mapping[str, Any] | None],
):
    async with TaskGroup() as group:
        for manager, products in meta_products.items():
            group.create_task(
                generate_manager(
                    debug,
                    cache_path,
                    generators_path,
                    meta_options.get(manager),
                    products,
                    generators - builtin_generators.keys(),
                    manager,
                )
            )

        for generator in generators & builtin_generators.keys():
            builtin_generators[generator](generators_path, meta_products)
