from collections.abc import Iterable, Mapping, Set
from typing import Any
from typing import cast as type_cast

from PPpackage_utils.parse import FrozenAny, json_check_format
from PPpackage_utils.utils import (
    MyException,
    ResolutionGraph,
    ResolutionGraphJSON,
    ResolutionGraphNodeValue,
    frozendict,
)
from pydantic import BaseModel


class Input(BaseModel):
    requirements: Mapping[str, Set[FrozenAny]]
    options: Mapping[str, Mapping[str, Any] | None]
    generators: Set[str]


def check_resolution_graph(
    debug: bool,
    resolution_json: Any,
) -> ResolutionGraphJSON:
    return type_cast(
        ResolutionGraphJSON,
        json_check_format(
            debug,
            resolution_json,
            {"roots", "graph"},
            set(),
            "Invalid resolution format.",
        ),
    )


def check_resolution_graphs(
    debug: bool,
    resolutions_json: Any,
) -> Iterable[Any]:
    if type(resolutions_json) is not list:
        raise MyException("Invalid resolutions format.")

    return resolutions_json


def parse_resolution_graph(
    debug: bool,
    resolution_graph_json: Any,
) -> ResolutionGraph:
    resolution_checked = check_resolution_graph(debug, resolution_graph_json)

    roots = tuple(frozenset(root) for root in resolution_checked["roots"])

    nodes = frozendict(
        {
            name: ResolutionGraphNodeValue(
                node_json["version"],
                frozenset(node_json["dependencies"]),
                frozendict(
                    {
                        manager: frozenset(requirements)
                        for manager, requirements in node_json["requirements"].items()
                    }
                ),
            )
            for name, node_json in resolution_checked["graph"].items()
        }
    )

    return ResolutionGraph(roots, nodes)


def parse_resolution_graphs(
    debug: bool,
    resolutions_json: Any,
) -> Set[ResolutionGraph]:
    resolution_graphs_checked = check_resolution_graphs(debug, resolutions_json)

    resolution_graphs = frozenset(
        parse_resolution_graph(debug, resolution_graph_json)
        for resolution_graph_json in resolution_graphs_checked
    )

    return resolution_graphs
