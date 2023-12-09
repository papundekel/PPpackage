from asyncio import Task, TaskGroup
from collections.abc import Mapping, MutableMapping, MutableSequence, Set
from itertools import chain
from sys import stderr
from typing import Any, Iterable

from PPpackage_utils.parse import (
    ManagerAndName,
    Options,
    Product,
    dump_many,
    dump_one,
    load_bytes_chunked,
    load_one,
)
from PPpackage_utils.utils import (
    SubmanagerCommand,
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
)

from .generators import builtin as builtin_generators
from .utils import Connections, NodeData, SubmanagerCommandFailure, data_to_product


async def generate_manager(
    debug: bool,
    connections: Connections,
    strict_connection: bool,
    options: Options,
    products: Iterable[Product],
    generators: Set[str],
    manager: str,
) -> memoryview:
    reader, writer = await connections.connect(manager, strict=strict_connection)

    await dump_one(debug, writer, SubmanagerCommand.GENERATE)
    await dump_one(debug, writer, options)
    await dump_many(debug, writer, products)
    await dump_many(debug, writer, generators)

    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(f"{manager} failed to create generators.")

    generators_directory = await load_bytes_chunked(debug, reader)

    return generators_directory


def check_results(
    tasks: Iterable[Task[memoryview | None]],
) -> Iterable[memoryview] | None:
    generators_directories: MutableSequence[memoryview] = []

    for task in tasks:
        generators_directory = task.result()

        if generators_directory is None:
            return None

        generators_directories.append(generators_directory)

    return generators_directories


async def generate(
    debug: bool,
    connections: Connections,
    strict_connection: bool,
    generators: Iterable[str],
    nodes: Iterable[tuple[ManagerAndName, NodeData]],
    meta_options: Mapping[str, Mapping[str, Any] | None],
) -> memoryview:
    stderr.write("Generating")
    for generator in generators:
        stderr.write(f" {generator}")
    stderr.write(" for...\n")

    for manager_and_name, _ in nodes:
        package_name = manager_and_name.name

        stderr.write(f"\t{package_name}\n")

    meta_products: MutableMapping[str, MutableSequence[Product]] = {}

    for manager_and_package, data in nodes:
        meta_products.setdefault(manager_and_package.manager, []).append(
            data_to_product(manager_and_package.name, data)
        )

    tasks: MutableSequence[Task[memoryview]] = []
    builtin_directories: MutableSequence[memoryview] = []

    async with TaskGroup() as group:
        for manager, products in meta_products.items():
            tasks.append(
                group.create_task(
                    generate_manager(
                        debug,
                        connections,
                        strict_connection,
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
