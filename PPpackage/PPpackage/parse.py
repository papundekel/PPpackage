from collections.abc import Mapping, Sequence, Set
from sys import stderr
from typing import Any, Iterable, TypedDict
from typing import cast as type_cast

from PPpackage_utils.parse import json_check_format, parse_generators, parse_lockfile
from PPpackage_utils.utils import (
    MyException,
    ResolutionGraph,
    ResolutionGraphJSON,
    ResolutionGraphNodeValue,
    frozendict,
)


def check_requirements(debug: bool, requirements_json: Any) -> Iterable[Any]:
    if type(requirements_json) is not list:
        if debug:
            print(
                f"Got {requirements_json}.",
                file=stderr,
            )
        raise MyException(
            "Invalid meta requirements format. Manager requirements should be a list."
        )

    return requirements_json


def parse_requirements(debug: bool, requirements_json: Any) -> Set[Any]:
    requirements_checked = check_requirements(debug, requirements_json)

    requirements = frozenset(requirements_checked)

    return requirements


def check_meta_requirements(
    debug: bool, meta_requirements_json: Any
) -> Mapping[str, Any]:
    if type(meta_requirements_json) is not frozendict:
        raise MyException("Invalid requirements format. Should be a dictionary.")

    return meta_requirements_json


def parse_meta_requirements(
    debug: bool, meta_requirements_json: Any
) -> Mapping[str, Set[Any]]:
    meta_requirements_checked = check_meta_requirements(debug, meta_requirements_json)

    meta_requirements = frozendict(
        {
            manager: parse_requirements(debug, requirements_json)
            for manager, requirements_json in meta_requirements_checked.items()
        }
    )

    return meta_requirements


def check_meta_options(meta_options_json: Any) -> Mapping[str, Mapping[str, Any]]:
    if type(meta_options_json) is not frozendict:
        raise MyException("Invalid meta options format.")

    for options_json in meta_options_json.values():
        # TODO: rethink
        if type(options_json) is not frozendict:
            raise MyException("Invalid options format.")

    return meta_options_json


def parse_meta_options(meta_options_json: Any) -> Mapping[str, Mapping[str, Any]]:
    meta_options_checked = check_meta_options(meta_options_json)

    return meta_options_checked


class Input(TypedDict):
    requirements: Any
    options: Any
    generators: Any


def check_input(debug: bool, input_json: Any) -> Input:
    return type_cast(
        Input,
        json_check_format(
            debug,
            input_json,
            {"requirements", "options", "generators"},
            set(),
            "Invalid input format.",
        ),
    )


def parse_input(
    debug: bool,
    input_json: Any,
) -> tuple[Mapping[str, Set[Any]], Mapping[str, Mapping[str, Any] | None], Set[str]]:
    input_checked = check_input(debug, input_json)

    meta_requirements = parse_meta_requirements(debug, input_checked["requirements"])
    meta_options = parse_meta_options(input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return meta_requirements, meta_options, generators


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
