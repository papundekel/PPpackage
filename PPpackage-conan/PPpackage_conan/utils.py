from collections.abc import Mapping
from os import environ
from pathlib import Path
from typing import Any, TypeVar

from PPpackage_utils.validation import load_from_bytes, load_object
from pydantic import BaseModel


class DependencyValueJSON(BaseModel):
    direct: bool


class BaseNode(BaseModel):
    id: str
    ref: str
    user: str | None
    name: str
    version: str
    rrev: str

    def get_version(self) -> str:
        return f"{self.version}#{self.rrev}"


class FetchNode(BaseNode):
    package_id: str
    prev: str
    cpp_info: Mapping[str, Any]

    def get_product_id(self) -> str:
        return f"{self.package_id}#{self.prev}"


class ResolveNode(BaseNode):
    dependencies: Mapping[str, DependencyValueJSON]


class ConanGraphNodes(BaseModel):
    nodes: Mapping[str, Mapping[str, Any]]


class ConanGraph(BaseModel):
    graph: ConanGraphNodes


T = TypeVar("T", bound=BaseModel)


def parse_conan_graph_nodes(
    NodeType: type[T], conan_graph_json_bytes: bytes
) -> Mapping[str, T]:
    conan_graph = load_from_bytes(ConanGraph, memoryview(conan_graph_json_bytes))

    return {
        node_id: load_object(NodeType, node_json)
        for node_id, node_json in conan_graph.graph.nodes.items()
        if node_id != "0"
    }


def make_conan_environment(cache_path: Path) -> Mapping[str, str]:
    environment = environ.copy()

    # CONAN_HOME must be an absolute path
    environment["CONAN_HOME"] = str(cache_path.absolute())

    return environment
