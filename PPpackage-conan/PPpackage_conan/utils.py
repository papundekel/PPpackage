from collections.abc import Generator, Mapping
from contextlib import contextmanager
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Optional, TypedDict

from jinja2 import Template as Jinja2Template
from PPpackage_utils.utils import json_loads


def get_cache_path(cache_path: Path) -> Path:
    return cache_path / "conan"


class DependencyValueJSON(TypedDict):
    direct: bool


class Node(TypedDict):
    id: str
    ref: str
    user: str
    name: str
    version: str
    rrev: str
    package_id: str
    prev: str
    cpp_info: Mapping[str, Any]
    dependencies: Mapping[str, DependencyValueJSON]


def parse_conan_graph_nodes(
    graph_string: str,
) -> Mapping[str, Node]:
    return {
        node["id"]: node
        for node in json_loads(graph_string)["graph"]["nodes"].values()
        if node["ref"] != ""
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


class GraphInfo:
    def __init__(self, node: Node):
        self.version = f"{node['version']}#{node['rrev']}"
        self.product_id = f"{node['package_id']}#{node['prev']}"
        self.cpp_info = node["cpp_info"]


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
