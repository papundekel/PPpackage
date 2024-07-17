from collections.abc import Iterable
from itertools import islice

from networkx import MultiDiGraph, dfs_preorder_nodes

from .schemes.node import NodeData


def get_graph_items(graph: MultiDiGraph) -> Iterable[tuple[str, NodeData]]:
    return graph.nodes.items()


def successors(graph: MultiDiGraph, package: str) -> Iterable[tuple[str, NodeData]]:
    for successor in islice(dfs_preorder_nodes(graph, source=package), 1, None):
        yield successor, graph.nodes[successor]
