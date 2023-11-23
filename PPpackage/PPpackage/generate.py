from asyncio import Task, TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Mapping, MutableMapping, MutableSequence, Set
from itertools import chain
from pathlib import Path
from typing import Any, Iterable

from PPpackage_utils.parse import (
    ManagerAndName,
    Options,
    Product,
    dump_many,
    dump_one,
    load_bytes,
)
from PPpackage_utils.utils import (
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
    asubprocess_wait,
    debug_redirect_stderr,
)

from .generators import builtin as builtin_generators
from .utils import NodeData, data_to_product


async def generate_manager(
    debug: bool,
    cache_path: Path,
    options: Options,
    products: Iterable[Product],
    generators: Set[str],
    manager: str,
) -> bytes:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "generate",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=debug_redirect_stderr(debug),
    )

    assert process.stdin is not None
    assert process.stdout is not None

    await dump_one(debug, process.stdin, options)
    await dump_many(debug, process.stdin, products)
    await dump_many(debug, process.stdin, generators)

    generators_bytes = await load_bytes(debug, process.stdout)

    await asubprocess_wait(process, f"Error in {manager}'s generate.")

    return generators_bytes


async def generate(
    debug: bool,
    cache_path: Path,
    generators: Iterable[str],
    nodes: Iterable[tuple[ManagerAndName, NodeData]],
    meta_options: Mapping[str, Mapping[str, Any] | None],
) -> bytes:
    meta_products: MutableMapping[str, MutableSequence[Product]] = {}

    for manager_and_package, data in nodes:
        meta_products.setdefault(manager_and_package.manager, []).append(
            data_to_product(manager_and_package.name, data)
        )

    tasks: MutableSequence[Task[bytes]] = []
    builtin_directories: MutableSequence[bytes] = []

    async with TaskGroup() as group:
        for manager, products in meta_products.items():
            tasks.append(
                group.create_task(
                    generate_manager(
                        debug,
                        cache_path,
                        meta_options.get(manager),
                        products,
                        generators - builtin_generators.keys(),
                        manager,
                    )
                )
            )

        for generator in generators & builtin_generators.keys():
            builtin_directories.append(builtin_generators[generator](meta_products))

    with TarFileInMemoryWrite() as merged_tar:
        for generators_directory in chain(
            builtin_directories, (task.result() for task in tasks)
        ):
            with TarFileInMemoryRead(generators_directory) as tar:
                for member in tar:
                    merged_tar.addfile(
                        tar.getmember(member.name), tar.extractfile(member)
                    )

    return merged_tar.data
