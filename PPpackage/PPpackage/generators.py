from collections.abc import Callable, Mapping
from json import dump as json_dump
from pathlib import Path

from PPpackage_utils.utils import ensure_dir_exists


def versions(
    generators_path: Path,
    manager_versions_dict: Mapping[str, Mapping[str, str]],
    manager_product_ids: Mapping[str, Mapping[str, str]],
) -> None:
    versions_path = generators_path / "versions"

    for manager, versions in manager_versions_dict.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        product_ids = manager_product_ids[manager]

        for package, version in versions.items():
            product_id = product_ids[package]

            with (manager_path / f"{package}.json").open("w") as versions_file:
                json_dump(
                    {"version": version, "product_id": product_id},
                    versions_file,
                    indent=4,
                )


builtin: Mapping[
    str,
    Callable[
        [Path, Mapping[str, Mapping[str, str]], Mapping[str, Mapping[str, str]]], None
    ],
] = {"versions": versions}
