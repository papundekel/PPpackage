from asyncio import Task, TaskGroup
from collections.abc import Mapping, MutableMapping, MutableSequence
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Iterable

from PPpackage_submanager.schemes import ManagerAndName, Options, Product
from PPpackage_utils.utils import ensure_dir_exists, movetree

from .generators import builtin as builtin_generators
from .submanager import Submanager
from .utils import NodeData, data_to_product


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
    submanagers: Mapping[str, Submanager],
    generators: Iterable[str],
    nodes: Iterable[tuple[ManagerAndName, NodeData]],
    meta_options: Mapping[str, Options],
    destination_path: Path,
) -> None:
    stderr.write("Generating")
    for generator in generators:
        stderr.write(f" {generator}")
    stderr.write(" for...\n")

    ensure_dir_exists(destination_path)

    for manager_and_name, _ in nodes:
        package_name = manager_and_name.name

        stderr.write(f"\t{package_name}\n")

    meta_products: MutableMapping[str, MutableSequence[Product]] = {}

    for manager_and_package, data in nodes:
        meta_products.setdefault(manager_and_package.manager, []).append(
            data_to_product(manager_and_package.name, data)
        )

    directories: MutableSequence[Path] = []

    async with TaskGroup() as group:
        for submanager_name, products in meta_products.items():
            submanager = submanagers[submanager_name]

            submanager_destination_path = Path(mkdtemp())

            group.create_task(
                submanager.generate(
                    meta_options.get(submanager_name),
                    products,
                    generators - builtin_generators.keys(),
                    submanager_destination_path,
                )
            )

            directories.append(submanager_destination_path)

        for generator in generators & builtin_generators.keys():
            submanager_destination_path = Path(mkdtemp())
            builtin_generators[generator](meta_products, submanager_destination_path)

            directories.append(submanager_destination_path)

    for directory in directories:
        movetree(directory, destination_path)
        directory.rmdir()
