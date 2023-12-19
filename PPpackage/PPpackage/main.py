import itertools
from collections.abc import (
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
)
from pathlib import Path
from platform import node
from sys import stderr, stdin

from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx import topological_generations as base_topological_generations
from networkx.drawing.nx_pydot import to_pydot
from PPpackage_utils.parse import ManagerAndName, load_from_bytes
from PPpackage_utils.utils import tar_archive, tar_extract
from pydantic import ValidationError
from pydot import Dot

from .fetch import fetch
from .generate import generate
from .install import install
from .parse import Input
from .resolve import resolve
from .update_database import update_database
from .utils import Connections, NodeData, SubmanagerCommandFailure


def topological_generations(
    graph: MultiDiGraph,
) -> Iterable[Mapping[str, Sequence[tuple[str, NodeData]]]]:
    for generation in base_topological_generations(graph):
        manager_nodes: MutableMapping[str, MutableSequence[tuple[str, NodeData]]] = {}

        for manager_and_name in generation:
            manager_nodes.setdefault(manager_and_name.manager, []).append(
                (manager_and_name.name, graph.nodes[manager_and_name])
            )

        yield manager_nodes


def topological_test_visit(
    graph: MultiDiGraph, seen: MutableSet[ManagerAndName], node: ManagerAndName
) -> Iterable[ManagerAndName]:
    if node not in seen:
        seen.add(node)

        successor_map = {}
        for successor in graph.successors(node):
            successor_map.setdefault(successor.manager, []).append(successor)

        successors_same_manager = successor_map.get(node.manager, [])
        for successor in successors_same_manager:
            yield from topological_test_visit(graph, seen, successor)
        successor_map.pop(node.manager, None)

        for successors in successor_map.values():
            for successor in successors:
                yield from topological_test_visit(graph, seen, successor)

        yield node


def topological_test_iteration(
    graph: MultiDiGraph,
    sources: MutableSet[ManagerAndName],
    seen: MutableSet[ManagerAndName],
) -> Iterable[ManagerAndName]:
    while len(sources) != 0:
        node = sources.pop()

        if node in seen:
            continue

        yield from topological_test_visit(graph, seen, node)


def topological_test(graph: MultiDiGraph) -> Iterable[ManagerAndName]:
    seen = set[ManagerAndName]()

    sources = {node for node, d in graph.in_degree() if d == 0}
    same_manager_sources = {
        node
        for node in sources
        if all(
            successor.manager == node.manager for successor in graph.successors(node)
        )
    }
    sources = sources - same_manager_sources

    same_manager_mapping = dict[str, MutableSet[ManagerAndName]]()
    for node in same_manager_sources:
        same_manager_mapping.setdefault(node.manager, set()).add(node)

    for same_manager_sources in same_manager_mapping.values():
        yield from topological_test_iteration(graph, same_manager_sources, seen)
    yield from topological_test_iteration(graph, sources, seen)


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


async def main(
    debug: bool,
    do_update_database: bool,
    submanager_socket_paths: Mapping[str, Path],
    destination_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
    resolve_iteration_limit: int,
) -> None:
    try:
        connections = Connections(submanager_socket_paths)

        async with connections.communicate(debug):
            input_json_bytes = stdin.buffer.read()

            try:
                input = load_from_bytes(debug, Input, input_json_bytes)
            except ValidationError as e:
                stderr.write("ERROR: Invalid input.\n")
                stderr.write(e.json(indent=4))

                return

            if do_update_database:
                managers = input.requirements.keys()
                await update_database(debug, connections, managers)

            options = input.options if input.options is not None else {}

            graph = await resolve(
                debug,
                resolve_iteration_limit,
                connections,
                input.requirements,
                options,
            )

            if graph_path is not None:
                graph_to_dot(graph, graph_path)

            reversed_graph = graph.reverse(copy=False)

            generations = list(topological_generations(reversed_graph))

            await fetch(debug, connections, options, graph, generations)

            old_installation = tar_archive(destination_path)

            new_installation = await install(
                debug, connections, old_installation, generations
            )

            if generators_path is not None and input.generators is not None:
                generators_directory = await generate(
                    debug,
                    connections,
                    True,
                    input.generators,
                    graph.nodes(data=True),
                    options,
                )
                tar_extract(generators_directory, generators_path)

            tar_extract(new_installation, destination_path)

            stderr.write("Done.\n")
    except* SubmanagerCommandFailure as e_group:
        log_exception(e_group)
        stderr.write("Aborting.\n")
