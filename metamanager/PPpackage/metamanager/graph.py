from collections.abc import Iterable

from networkx import MultiDiGraph

from .schemes.node import NodeData


def get_graph_items(graph: MultiDiGraph) -> Iterable[tuple[str, NodeData]]:
    return graph.nodes.items()
