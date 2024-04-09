from collections.abc import Iterable
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from typing import IO

from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from PPpackage_repository_driver.schemes import Package
from PPpackage_utils.validation import load_from_bytes
from pydantic import ValidationError
from pydot import Dot

from .exceptions import SubmanagerCommandFailure
from .resolve import resolve
from .schemes import Config, Input, ResolutionModel
from .submanagers import Repositories

logger = getLogger(__name__)


def graph_to_dot(graph: MultiDiGraph, path: Path) -> None:
    namespace_to_color = {}

    for node in graph.nodes():
        if node.namespace not in namespace_to_color:
            namespace_to_color[node.namespace] = len(namespace_to_color) + 1

    graph_presentation: MultiDiGraph = convert_node_labels_to_integers(
        graph, label_attribute="node"
    )

    for _, data in graph_presentation.nodes(data=True):
        node: Package = data["node"]
        version: str = data["version"]

        data.clear()

        data["label"] = f'"{node.namespace}\n{node.name}\n{version}"'
        data["fillcolor"] = namespace_to_color[node.namespace]

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


def build_graph(model: ResolutionModel) -> MultiDiGraph:
    return MultiDiGraph()  # TODO


def select_best_model(models: Iterable[ResolutionModel]) -> ResolutionModel:
    # TODO

    for model in models:
        return model

    raise SubmanagerCommandFailure("No model found.")


async def main(
    workdir_path: Path,
    config_path: Path,
    destination_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
) -> None:
    config = parse_config(config_path)

    async with Repositories(
        config.repository_drivers, config.repositories
    ) as repositories:
        input = parse_input(stdin.buffer)

        try:
            models = await resolve(repositories, input.requirements, input.options)

            model = select_best_model(models)

            graph = build_graph(model)

            if graph_path is not None:
                graph_to_dot(graph, graph_path)

            # TODO fetch, install, generate

            stderr.write("Done.\n")

        except* SubmanagerCommandFailure as e_group:
            log_exception(e_group)
            stderr.write("Aborting.\n")
