from collections.abc import Iterable, MutableSet
from pathlib import Path
from sys import stderr, stdin

from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx import topological_generations as base_topological_generations
from networkx.drawing.nx_pydot import to_pydot
from PPpackage_submanager.schemes import ManagerAndName
from PPpackage_utils.validation import load_from_bytes
from pydantic import ValidationError
from pydot import Dot

from .fetch import fetch
from .generate import generate
from .install import install
from .resolve import resolve
from .schemes import Input
from .settings import Settings
from .submanagers import Submanagers
from .update_database import update_database
from .utils import NodeData, SubmanagerCommandFailure


def topological_generations(
    graph: MultiDiGraph,
) -> Iterable[Iterable[tuple[ManagerAndName, NodeData]]]:
    for generation in base_topological_generations(graph):
        yield [(node, graph.nodes[node]) for node in generation]


def install_topology_visit(
    graph: MultiDiGraph, seen: MutableSet[ManagerAndName], node: ManagerAndName
) -> Iterable[tuple[ManagerAndName, NodeData]]:
    if node not in seen:
        seen.add(node)

        successor_map = {}
        for successor in graph.successors(node):
            successor_map.setdefault(successor.manager, []).append(successor)

        successors_same_manager = successor_map.pop(node.manager, [])

        for successors in successor_map.values():
            for successor in successors:
                yield from install_topology_visit(graph, seen, successor)

        for successor in successors_same_manager:
            yield from install_topology_visit(graph, seen, successor)

        yield node, graph.nodes[node]


def create_install_topology_iteration(
    graph: MultiDiGraph,
    sources: MutableSet[ManagerAndName],
    seen: MutableSet[ManagerAndName],
) -> Iterable[tuple[ManagerAndName, NodeData]]:
    while len(sources) != 0:
        node = sources.pop()

        if node in seen:
            continue

        yield from install_topology_visit(graph, seen, node)


def create_install_topology(
    graph: MultiDiGraph,
) -> Iterable[tuple[ManagerAndName, NodeData]]:
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
        yield from create_install_topology_iteration(graph, same_manager_sources, seen)
    yield from create_install_topology_iteration(graph, sources, seen)


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
    workdir_path: Path,
    do_update_database: bool,
    settings: Settings,
    destination_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
    resolve_iteration_limit: int,
) -> None:
    try:
        async with Submanagers(settings.submanagers) as submanagers:
            input_json_bytes = stdin.buffer.read()

            try:
                input = load_from_bytes(Input, memoryview(input_json_bytes))
            except ValidationError as e:
                stderr.write("ERROR: Invalid input.\n")
                stderr.write(e.json(indent=4))

                return

            if do_update_database:
                submanager_names = input.requirements.keys()
                await update_database(submanagers, submanager_names)

            options = input.options if input.options is not None else {}

            graph = await resolve(
                submanagers,
                resolve_iteration_limit,
                input.requirements,
                options,
            )

            if graph_path is not None:
                graph_to_dot(graph, graph_path)

            reversed_graph = graph.reverse(copy=False)

            fetch_order = topological_generations(reversed_graph)
            install_order = list(create_install_topology(graph))

            await fetch(
                workdir_path, submanagers, options, graph, fetch_order, install_order
            )

            await install(submanagers, install_order, destination_path)

            if generators_path is not None and input.generators is not None:
                await generate(
                    submanagers,
                    input.generators,
                    graph.nodes(data=True),
                    options,
                    generators_path,
                )

            stderr.write("Done.\n")

    except* SubmanagerCommandFailure as e_group:
        log_exception(e_group)
        stderr.write("Aborting.\n")
