from collections.abc import Iterable, MutableSet

from networkx import MultiDiGraph
from PPpackage_submanager.schemes import ManagerAndName

from .utils import NodeData


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
