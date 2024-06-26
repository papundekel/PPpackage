from asyncio import TaskGroup
from collections.abc import Mapping
from pathlib import Path

from networkx import MultiDiGraph, topological_generations

from .installer import Installer
from .schemes.node import NodeData


async def install(
    installers: Mapping[str, Installer], graph: MultiDiGraph, installation_path: Path
):
    for generation in topological_generations(graph.reverse(copy=False)):
        async with TaskGroup() as group:
            for package in generation:
                node_data: NodeData = graph.nodes[package]

                product_path, installer_identifier = await node_data["product"]

                installer = installers[installer_identifier]

                group.create_task(installer.install(product_path, installation_path))
