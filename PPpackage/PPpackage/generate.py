from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any, Iterable

from PPpackage_utils.parse import GenerateInput, GenerateInputPackagesValue, model_dump
from PPpackage_utils.utils import asubprocess_communicate

from .generators import builtin as builtin_generators
from .sub import generate as PP_generate


async def generate_external_manager(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    input: GenerateInput,
    manager: str,
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

    input_json_bytes = model_dump(debug, input)

    await asubprocess_communicate(
        await process,
        f"Error in {manager}'s generate.",
        input_json_bytes,
    )


async def generate_manager(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    input: GenerateInput,
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
        input=input,
    )


async def generate(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    generators: Iterable[str],
    meta_packages: Mapping[str, Mapping[str, GenerateInputPackagesValue]],
    meta_options: Mapping[str, Mapping[str, Any] | None],
):
    async with TaskGroup() as group:
        for manager, packages in meta_packages.items():
            group.create_task(
                generate_manager(
                    debug,
                    cache_path,
                    generators_path,
                    GenerateInput(
                        generators=generators - builtin_generators.keys(),
                        packages=packages,
                        options=meta_options.get(manager),
                    ),
                    manager,
                )
            )

        for generator in generators & builtin_generators.keys():
            builtin_generators[generator](generators_path, meta_packages)
