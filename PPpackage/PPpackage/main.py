from asyncio import StreamReader, StreamWriter
from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence
from pathlib import Path
from sys import stderr, stdin

from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx import topological_generations as base_topological_generations
from networkx.drawing.nx_pydot import to_pydot
from PPpackage_utils.parse import ManagerAndName, load_from_bytes
from PPpackage_utils.utils import tar_archive, tar_extract
from pydot import Dot

from .fetch import fetch
from .generate import generate
from .install import install
from .parse import Input
from .resolve import resolve
from .update_database import update_database
from .utils import NodeData, SubmanagerCommandFailure, communicate_with_submanagers


def topological_generations(
    graph: MultiDiGraph,
) -> Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]]:
    for generation in base_topological_generations(graph):
        manager_nodes: MutableMapping[str, MutableSequence[tuple[str, NodeData]]] = {}

        for manager_and_name in generation:
            manager_nodes.setdefault(manager_and_name.manager, []).append(
                (manager_and_name.name, graph.nodes[manager_and_name])
            )

        yield manager_nodes


def graph_to_dot(graph: MultiDiGraph, path: Path) -> None:
    manager_to_color = {}

    for node in graph.nodes():
        if node.manager not in manager_to_color:
            manager_to_color[node.manager] = len(manager_to_color) + 1

    graph_presentation: MultiDiGraph = convert_node_labels_to_integers(
        graph, label_attribute="node"
    )

    for _, data in graph_presentation.nodes(data=True):
        node: ManagerAndName = data["node"]
        version: str = data["version"]

        data.clear()

        data["label"] = f'"{node.manager}\n{node.name}\n{version}"'
        data["fillcolor"] = manager_to_color[node.manager]

    graph_presentation.graph.update(
        {
            "node": {
                "colorscheme": "accent8",
                "style": "filled",
                "shape": "box",
            }
        }
    )

    dot: Dot = to_pydot(graph_presentation)

    dot.write(path)


def log_exception(e: BaseExceptionGroup) -> None:
    for e in e.exceptions:
        if isinstance(e, ExceptionGroup):
            log_exception(e)
        else:
            stderr.write(f"{e.message}\n")


async def main(
    debug: bool,
    do_update_database: bool,
    submanager_socket_paths: Mapping[str, Path],
    generators_path: Path,
    destination_path: Path,
    graph_path: Path | None,
    resolve_iteration_limit: int,
) -> None:
    try:
        connections: MutableMapping[str, tuple[StreamReader, StreamWriter]] = {}

        async with communicate_with_submanagers(debug, connections):
            input_json_bytes = stdin.buffer.read()

            input = load_from_bytes(debug, Input, input_json_bytes)

            if do_update_database:
                managers = input.requirements.keys()
                await update_database(
                    debug, submanager_socket_paths, connections, managers
                )

            graph = await resolve(
                debug,
                resolve_iteration_limit,
                submanager_socket_paths,
                connections,
                input.requirements,
                input.options,
            )

            if graph_path is not None:
                graph_to_dot(graph, graph_path)

            reversed_graph = graph.reverse(copy=False)

            generations = list(topological_generations(reversed_graph))

            await fetch(debug, connections, input.options, graph, generations)

            generators = await generate(
                debug,
                connections,
                input.generators,
                graph.nodes(data=True),
                input.options,
            )

            old_installation = tar_archive(destination_path)

            new_installation = await install(
                debug, connections, old_installation, generations
            )

            tar_extract(generators, generators_path)
            tar_extract(new_installation, destination_path)

            stderr.write("Done.\n")
    except* SubmanagerCommandFailure as e_group:
        log_exception(e_group)
        stderr.write("Aborting.\n")
