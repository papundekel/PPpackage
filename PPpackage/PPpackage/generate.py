from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Mapping, Set
from functools import partial
from pathlib import Path
from typing import Any, Iterable

from PPpackage_utils.parse import GenerateInput, Options, Product, model_dump_stream
from PPpackage_utils.utils import asubprocess_wait

from .generators import builtin as builtin_generators
from .sub import generate as PP_generate


async def generate_external_manager(
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
        stdout=PIPE,
        stderr=None,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    model_dump_stream(
        debug,
        process.stdin,
        GenerateInput(options=options, products=products, generators=generators),
    )
    await process.stdin.drain()

    await asubprocess_wait(process, f"Error in {manager}'s generate.")


async def generate_manager(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    options: Options,
    products: Iterable[Product],
    generators: Set[str],
    manager: str,
) -> None:
    if manager == "PP":
        generate = PP_generate
    else:
        generate = partial(generate_external_manager, manager=manager)

    await generate(
        debug=debug,
        cache_path=cache_path,
        generators_path=generators_path,
        options=options,
        products=products,
        generators=generators,
    )


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
