from collections.abc import AsyncIterable, Iterable, Mapping
from pathlib import Path

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
    dependency_set = {manager_and_name for manager_and_name, _ in dependencies}

    dependency_install_order = [
        (node, data) for node, data in install_order if node in dependency_set
    ]

    return await install(submanagers, dependency_install_order, destination_path)


async def fetch_generate(
    submanagers: Mapping[str, Submanager],
    generators: AsyncIterable[str],
    nodes: Iterable[tuple[ManagerAndName, NodeData]],
    meta_options: Mapping[str, Options],
    destination_path: Path,
):
    generators_list = [generator async for generator in generators]

    await generate(submanagers, generators_list, nodes, meta_options, destination_path)
