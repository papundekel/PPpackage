from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, Set
from pathlib import Path
from typing import Any

from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from pydot import Dot

from .graph import get_graph_items
from .repository import Repository


async def get_package_detail(
    repositories: Iterable[Repository],
    repository_to_translated_options: Mapping[Repository, Any],
    graph: MultiDiGraph,
    variable: str,
) -> None:
    async with TaskGroup() as group:
        tasks = [
            group.create_task(
                repository.get_package_detail(
                    repository_to_translated_options[repository], variable
                )
            )
            for repository in repositories
        ]
    found = False
    for repository, task in zip(repositories, tasks):
        package_detail = task.result()

        if package_detail is not None:
            graph.add_node(variable, repository=repository, detail=package_detail)
            found = True
            break

    if not found:
        print(f"Package {variable} not found in any repository")


async def get_package_details(
    repositories: Iterable[Repository],
    repository_to_translated_options: Mapping[Repository, Any],
    model: Set[str],
) -> MultiDiGraph:
    graph = MultiDiGraph()

    async with TaskGroup() as group:
        for variable in model:
            group.create_task(
                get_package_detail(
                    repositories, repository_to_translated_options, graph, variable
                )
            )

    return graph


def create_dependencies(graph: MultiDiGraph) -> None:
    edges = [
        (package, dependency)
        for package, package_data in get_graph_items(graph)
        for dependency, dependency_data in get_graph_items(graph)
        if any(
            interface in dependency_data["detail"].interfaces
            for interface in package_data["detail"].dependencies
        )
    ]

    graph.add_edges_from(edges)


async def create_graph(
    repositories: Iterable[Repository],
    repository_to_translated_options: Mapping[Repository, Any],
    model: Set[str],
) -> MultiDiGraph:
    graph = await get_package_details(
        repositories, repository_to_translated_options, model
    )

    create_dependencies(graph)

    return graph


def graph_to_dot(graph: MultiDiGraph) -> Dot:
    manager_to_color = dict[str, int]()

    for package, data in get_graph_items(graph):
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

        data["label"] = f'"{package}"'
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


def write_graph_to_file(graph: MultiDiGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    graph_dot = graph_to_dot(graph)
    graph_dot.write(path)
