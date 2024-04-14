from asyncio import create_task
from collections.abc import Iterable, Mapping
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from typing import IO, Any

from asyncstdlib import any as async_any
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from pydantic import ValidationError
from pydot import Dot

from PPpackage.utils.validation import load_from_bytes

from .exceptions import SubmanagerCommandFailure
from .fetch import fetch
from .install import install
from .repositories import Repositories
from .resolve import resolve
from .schemes import Config, Input, NodeData
from .translators import Translators

logger = getLogger(__name__)


def log_exception(e: BaseExceptionGroup) -> None:
    for e in e.exceptions:
        if isinstance(e, ExceptionGroup):
            log_exception(e)
        else:
            stderr.write(f"ERROR: {e.message}\n")


def parse_input(stdin: IO[bytes]) -> Input:
    input_json_bytes = stdin.read()

    try:
        input = load_from_bytes(Input, memoryview(input_json_bytes))
    except ValidationError as e:
        stderr.write("ERROR: Invalid input.\n")
        stderr.write(e.json(indent=4))

        raise

    return input


def parse_config(config_path: Path) -> Config:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = load_from_bytes(Config, memoryview(config_json_bytes))
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


def get_graph_items(graph: MultiDiGraph) -> Iterable[tuple[str, NodeData]]:
    return graph.nodes.items()


def get_package_details(graph: MultiDiGraph) -> None:
    stderr.write("Fetching package details...\n")

    for package, node_data in get_graph_items(graph):
        node_data["detail"] = create_task(
            node_data["repository"].get_package_detail(package)
        )


async def create_dependencies(graph: MultiDiGraph) -> None:
    edges = [
        (package, dependency)
        for package, package_data in get_graph_items(graph)
        for dependency, dependency_data in get_graph_items(graph)
        if await async_any(
            interface in (await dependency_data["detail"]).interfaces
            for interface in (await package_data["detail"]).dependencies
        )
    ]

    graph.add_edges_from(edges)


def graph_to_dot(graph: MultiDiGraph) -> Dot:
    manager_to_color = dict[str, int]()

    packages: Iterable[tuple[str, Mapping[str, Any]]] = graph.nodes.items()

    for package, data in packages:
        repository_identifier = data["repository"].get_identifier()

        if repository_identifier not in manager_to_color:
            manager_to_color[repository_identifier] = len(manager_to_color) + 1

    graph_presentation: MultiDiGraph = convert_node_labels_to_integers(
        graph, label_attribute="package"
    )

    for _, data in graph_presentation.nodes.items():
        package: str = data["package"]
        repository = data["repository"]

        data.clear()

        data["label"] = package
        data["fillcolor"] = manager_to_color[repository.get_identifier()]

    graph_presentation.graph.update(
        {
            "graph": {
                "bgcolor": "black",
                "margin": 0,
            },
            "node": {
                "colorscheme": "accent8",
                "style": "filled",
                "shape": "box",
            },
            "edge": {
                "color": "white",
            },
        }
    )

    return to_pydot(graph_presentation)


async def generators(generators_path: Path) -> None:
    # TODO
    pass


async def main(
    config_path: Path,
    installation_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
) -> None:
    config = parse_config(config_path)

    translators = Translators(config.requirement_translators)

    async with Repositories(
        config.repository_drivers, config.repositories
    ) as repositories:
        input = parse_input(stdin.buffer)

        try:
            graph = await resolve(
                repositories,
                translators,
                input.requirements,
                input.options,
            )

            for package in sorted(graph.nodes):
                stderr.write(f"\t{package}\n")

            get_package_details(graph)

            await create_dependencies(graph)

            if graph_path is not None:
                graph_dot = graph_to_dot(graph)
                graph_dot.write(graph_path)

            await fetch(config.product_cache_path, graph)

            await install(installation_path)

            if generators_path is not None:
                await generators(generators_path)

            stderr.write("Done.\n")

        except* SubmanagerCommandFailure as e_group:
            log_exception(e_group)
            stderr.write("Aborting.\n")
