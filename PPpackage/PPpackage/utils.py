from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import IDAndInfo

machine_id_relative_path = Path("etc") / "machine-id"


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id


def register_product_id_and_info(
    manager: str,
    nodes: Mapping[tuple[str, str], MutableMapping[str, Any]],
    package_name: str,
    id_and_info: IDAndInfo,
) -> None:
    node = nodes[(manager, package_name)]
    node["product_id"] = id_and_info.product_id
    node["product_info"] = id_and_info.product_info
