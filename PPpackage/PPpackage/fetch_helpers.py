from asyncio import TaskGroup, create_subprocess_exec
from collections.abc import AsyncIterable, Iterable, Mapping
from pathlib import Path
from sys import stderr

from PPpackage_submanager.schemes import ManagerAndName, Options

from PPpackage.schemes import NodeData

from .generate import generate
from .install import install
from .submanager import Submanager


async def fetch_install(
    submanagers: Mapping[str, Submanager],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
):
    print("RECURSIVE INSTALL BEGIN", file=stderr)

    dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

    dependency_install_order = [
        (node, data) for node, data in install_order if node in dependency_set
    ]
    print(dependency_install_order, file=stderr)

    x = await install(submanagers, dependency_install_order, destination_path)

    print("RECURSIVE INSTALL DONE", file=stderr)

    return x


async def fetch_generate(
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    generators: AsyncIterable[str],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
):
    print("RECURSIVE GENERATE BEGIN", file=stderr)

    generators_list = [generator async for generator in generators]

    await generate(
        submanagers, generators_list, dependencies, meta_options, destination_path
    )

    print("RECURSIVE GENERATE DONE", file=stderr)


async def fetch_install_generate(
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Options],
    install_order: Iterable[tuple[ManagerAndName, NodeData]],
    dependencies: Iterable[tuple[ManagerAndName, NodeData]],
    generators: AsyncIterable[str],
    installation_path: Path,
    generators_path: Path,
):
    async with TaskGroup() as group:
        group.create_task(
            fetch_install(
                submanagers,
                install_order,
                dependencies,
                installation_path,
            )
        )
        group.create_task(
            fetch_generate(
                submanagers,
                meta_options,
                generators,
                dependencies,
                generators_path,
            )
        )
