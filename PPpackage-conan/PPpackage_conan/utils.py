from collections.abc import Generator, Mapping
from contextlib import contextmanager
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Optional, TypeVar

from jinja2 import Template as Jinja2Template
from PPpackage_utils.parse import model_validate, model_validate_obj
from pydantic import BaseModel


def get_cache_path(cache_path: Path) -> Path:
    return cache_path / "conan"


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
    debug: bool,
    NodeType: type[T],
    conan_graph_json_bytes: bytes,
) -> Mapping[str, T]:
    conan_graph = model_validate(False, ConanGraph, conan_graph_json_bytes)

    return {
        node_id: model_validate_obj(debug, NodeType, node_json)
        for node_id, node_json in conan_graph.graph.nodes.items()
        if node_id != "0"
    }


@contextmanager
def create_and_render_temp_file(
    template: Jinja2Template,
    template_context: Mapping[str, Any],
    suffix: Optional[str] = None,
) -> Generator[_TemporaryFileWrapper, Any, Any]:
    with NamedTemporaryFile(mode="w", suffix=suffix) as file:
        template.stream(**template_context).dump(file)

        file.flush()

        yield file


def make_conan_environment(cache_path: Path) -> Mapping[str, str]:
    environment = environ.copy()

    environment["CONAN_HOME"] = str(cache_path.absolute())

    return environment


def get_path(module) -> Path:
    return Path(module.__file__)


def get_package_paths():
    import PPpackage_conan

    from . import deployer

    data_path = get_path(PPpackage_conan).parent / "data"
    deployer_path = get_path(deployer)

    return data_path, deployer_path
