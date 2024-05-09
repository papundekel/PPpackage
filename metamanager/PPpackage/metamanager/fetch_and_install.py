from asyncio import TaskGroup
from collections.abc import Awaitable, Iterable, Mapping, Set
from pathlib import Path
from sys import stderr
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from PPpackage.container_utils import Containerizer
from pydot import Dot
from sqlitedict import SqliteDict

from PPpackage.translator.interface.schemes import Literal

from .fetch import fetch
from .graph import get_graph_items
from .install import install
from .installer import Installer
from .repository import Repository
from .translators import Translator


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
    stderr.write("Fetching package details...\n")

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


async def fetch_and_install(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    archive_client: HTTPClient,
    cache_mapping: SqliteDict,
    product_cache_path: Path,
    repositories: Iterable[Repository],
    repository_to_translated_options: Mapping[Repository, Any],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    installers: Mapping[str, Installer],
    installation_path: Path,
    graph_path: Path | None,
    build_options: Any,
    model: Set[str],
):
    graph = await get_package_details(
        repositories, repository_to_translated_options, model
    )

    for package in sorted(graph.nodes):
        stderr.write(f"\t{package}\n")

    create_dependencies(graph)

    if graph_path is not None:
        write_graph_to_file(graph, graph_path)

    fetch(
        containerizer,
        containerizer_workdir,
        repositories,
        repository_to_translated_options,
        translators_task,
        installers,
        cache_mapping,
        archive_client,
        product_cache_path,
        build_options,
        graph,
    )

    await install(installers, graph, installation_path)
