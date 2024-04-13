from asyncio import TaskGroup
from collections.abc import AsyncIterable, Iterable, Mapping, Set
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from typing import IO, Any

from asyncstdlib import min as async_min
from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from pydantic import ValidationError
from pydot import Dot
from sqlitedict import SqliteDict

from PPpackage.utils.validation import load_from_bytes

from .exceptions import SubmanagerCommandFailure
from .fetch import fetch
from .repositories import Repositories
from .repository import Repository
from .resolve import resolve
from .schemes import Config, Input
from .translators import Translators
from .utils import Result

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


async def get_package_details(graph: MultiDiGraph) -> None:
    stderr.write("Fetching package details...\n")

    async with TaskGroup() as group:
        for package, data in graph.nodes.items():
            repository: Repository = data["repository"]
            data["detail"] = group.create_task(repository.get_package_detail(package))

    for package, data in graph.nodes.items():
        data["detail"] = data["detail"].result()

    stderr.write("Package details fetched.\n")


async def create_dependencies(graph: MultiDiGraph) -> None:
    graph.add_edges_from(
        (package, dependency)
        for package, package_data in graph.nodes.items()
        for dependency, dependency_data in graph.nodes.items()
        if (
            any(
                interface in dependency_data["detail"].interfaces
                for interface in package_data["detail"].dependencies
            )
        )
    )


async def select_best_model(
    models: AsyncIterable[Set[str]],
    packages_to_repositories_result: Result[Mapping[str, tuple[Repository, Set[str]]]],
) -> MultiDiGraph:
    stderr.write("Selecting the best model...\n")

    # from models with the fewest packages
    # select the lexicographically smallest
    model_result: list[str] | None = await async_min(
        (sorted(model) async for model in models),
        key=lambda x: (len(x), x),  # type: ignore
        default=None,
    )

    if model_result is None:
        raise SubmanagerCommandFailure("No model found.")

    stderr.write("The best model selected.\n")

    graph = MultiDiGraph()

    packages_to_repositories = packages_to_repositories_result.value

    graph.add_nodes_from(
        (package, {"repository": packages_to_repositories[package][0]})
        for package in model_result
    )

    return graph


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


async def install(installation_path: Path) -> None:
    # TODO
    pass


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
            packages_with_repositories_result = Result[
                Mapping[str, tuple[Repository, Set[str]]]
            ]()
            models = resolve(
                repositories,
                translators,
                input.requirements,
                input.options,
                packages_with_repositories_result,
            )

            graph = await select_best_model(models, packages_with_repositories_result)

            print(graph.nodes(), file=stderr)

            await get_package_details(graph)

            await create_dependencies(graph)

            if graph_path is not None:
                graph_dot = graph_to_dot(graph)
                graph_dot.write(graph_path)

            async with HTTPClient(http2=True) as client:
                with SqliteDict(
                    config.product_cache_path / "mapping-db.sqlite"
                ) as product_cache_mapping:
                    await fetch(
                        product_cache_mapping, config.product_cache_path, client, graph
                    )

            await install(installation_path)

            if generators_path is not None:
                await generators(generators_path)

            stderr.write("Done.\n")

        except* SubmanagerCommandFailure as e_group:
            log_exception(e_group)
            stderr.write("Aborting.\n")
