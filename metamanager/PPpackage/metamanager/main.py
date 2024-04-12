from asyncio import TaskGroup
from collections.abc import AsyncIterable, Iterable, Mapping, Set
from logging import getLogger
from pathlib import Path
from struct import pack
from sys import stderr, stdin
from typing import IO

from asyncstdlib import min as async_min
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from pydantic import ValidationError
from pydot import Dot

from metamanager.PPpackage.metamanager.repository import Repository
from PPpackage.utils.validation import load_from_bytes

from .exceptions import SubmanagerCommandFailure
from .repositories import Repositories
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


async def build_graph(
    model: Set[str],
    packages_with_repositories: Mapping[str, tuple[Repository, Set[str]]],
) -> MultiDiGraph:
    async with TaskGroup() as group:
        tasks = {
            package: group.create_task(
                packages_with_repositories[package][0].get_package_detail(package)
            )
            for package in model
        }

    results = {package: task.result() for package, task in tasks.items()}

    graph = MultiDiGraph()

    graph.add_nodes_from(model)

    graph.add_edges_from(
        (package, dependency)
        for package, package_detail in results.items()
        for dependency, dependency_detail in results.items()
        if (
            any(
                interface in dependency_detail.interfaces
                for interface in package_detail.dependencies
            )
        )
    )

    return graph


async def select_best_model(models: AsyncIterable[Set[str]]) -> Set[str]:
    # from models with the fewest packages
    # select the lexicographically smallest
    model_result = await async_min(
        (sorted(model) async for model in models),
        key=lambda x: (len(x), x),  # type: ignore
        default=None,
    )

    if model_result is None:
        raise SubmanagerCommandFailure("No model found.")

    return set(model_result)


def graph_to_dot(
    graph: MultiDiGraph,
    packages_with_repositories: Mapping[str, tuple[Repository, Set[str]]],
    path: Path,
) -> None:
    manager_to_color = {}

    packages: Iterable[str] = graph.nodes()

    for package in packages:
        repository_identifier = packages_with_repositories[package][0].get_identifier()

        if repository_identifier not in manager_to_color:
            manager_to_color[repository_identifier] = len(manager_to_color) + 1

    graph_presentation: MultiDiGraph = convert_node_labels_to_integers(
        graph, label_attribute="package"
    )

    for _, data in graph_presentation.nodes(data=True):
        package: str = data["package"]

        data.clear()

        data["label"] = package
        data["fillcolor"] = manager_to_color[
            packages_with_repositories[package][0].get_identifier()
        ]

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

    dot: Dot = to_pydot(graph_presentation)

    dot.write(path)


async def main(
    workdir_path: Path,
    config_path: Path,
    destination_path: Path,
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

            model = await select_best_model(models)

            packages_with_repositories = packages_with_repositories_result.value

            print(model, file=stderr)

            graph = await build_graph(model, packages_with_repositories)

            if graph_path is not None:
                graph_to_dot(graph, packages_with_repositories, graph_path)

            # TODO fetch, install, generate

            stderr.write("Done.\n")

        except* SubmanagerCommandFailure as e_group:
            log_exception(e_group)
            stderr.write("Aborting.\n")
