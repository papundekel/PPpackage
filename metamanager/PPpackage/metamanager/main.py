from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, Set
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from traceback import print_exc
from typing import IO, Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from pydantic import ValidationError
from pydot import Dot
from sqlitedict import SqliteDict

from PPpackage.utils.validation import validate_json

from .fetch import fetch
from .install import install
from .installers import Installers
from .repository import Repositories, Repository
from .resolve import resolve
from .schemes import Config, Input
from .schemes.node import NodeData
from .translators import Translators

logger = getLogger(__name__)


def log_exception(e: BaseExceptionGroup) -> None:
    for e in e.exceptions:
        if isinstance(e, ExceptionGroup):
            log_exception(e)
        else:
            print_exc(file=stderr)


def parse_input(stdin: IO[bytes]) -> Input:
    input_json_bytes = stdin.read()

    try:
        input = validate_json(Input, input_json_bytes)
    except ValidationError as e:
        stderr.write("ERROR: Invalid input.\n")
        stderr.write(e.json(indent=4))

        raise

    return input


def parse_config(config_path: Path) -> Config:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = validate_json(Config, config_json_bytes)
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


def get_graph_items(graph: MultiDiGraph) -> Iterable[tuple[str, NodeData]]:
    return graph.nodes.items()


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

    for repository, task in zip(repositories, tasks):
        package_detail = task.result()

        if package_detail is not None:
            graph.add_node(variable, repository=repository, detail=package_detail)
            break


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

    installers = Installers(config.installers)

    input = parse_input(stdin.buffer)

    try:
        async with Repositories(
            config.repository_drivers, config.repositories
        ) as repositories:
            async with TaskGroup() as task_group:
                translators_task = task_group.create_task(
                    Translators(repositories, config.requirement_translators)
                )

                repository_to_translated_options, model = await resolve(
                    repositories, translators_task, input.options, input.requirement
                )

            graph = await get_package_details(
                repositories, repository_to_translated_options, model
            )

            for package in sorted(graph.nodes):
                stderr.write(f"\t{package}\n")

            create_dependencies(graph)

            if graph_path is not None:
                graph_path.parent.mkdir(parents=True, exist_ok=True)

                graph_dot = graph_to_dot(graph)
                graph_dot.write(graph_path)

            async with HTTPClient(http2=True) as archive_client:
                config.product_cache_path.mkdir(parents=True, exist_ok=True)

                with SqliteDict(
                    config.product_cache_path / "mapping.db"
                ) as cache_mapping:
                    fetch(
                        repositories,
                        translators_task,
                        cache_mapping,
                        archive_client,
                        config.product_cache_path,
                        repository_to_translated_options,
                        input.build_options,
                        graph,
                    )

                    await install(installers, graph, installation_path)

        if generators_path is not None:
            await generators(generators_path)

            stderr.write("Done.\n")

    except* Exception as e_group:
        log_exception(e_group)
        stderr.write("Aborting.\n")
