from collections.abc import Callable, Mapping
from json import dump as json_dump
from pathlib import Path

from PPpackage_utils.utils import ensure_dir_exists

from .utils import GraphInfo


def info(generators_path: Path, graph_infos: Mapping[str, GraphInfo]) -> None:
    info_path = generators_path / "info"
    ensure_dir_exists(info_path)

    for package, graph_info in graph_infos.items():
        with open(info_path / f"{package}.json", "w") as file:
            json_dump(graph_info.cpp_info, file, indent=4)


additional: Mapping[str, Callable[[Path, Mapping[str, GraphInfo]], None]] = {
    "info": info
}
