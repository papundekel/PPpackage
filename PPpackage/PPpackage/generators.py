from collections.abc import Callable, Mapping
from json import dump as json_dump
from pathlib import Path

from PPpackage_utils.parse import GenerateInputPackagesValue
from PPpackage_utils.utils import ensure_dir_exists


def versions(
    generators_path: Path,
    meta_packages: Mapping[str, Mapping[str, GenerateInputPackagesValue]],
) -> None:
    versions_path = generators_path / "versions"

    for manager, packages in meta_packages.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        for package, value in packages.items():
            with (manager_path / f"{package}.json").open("w") as versions_file:
                json_dump(
                    {"version": value.version, "product_id": value.product_id},
                    versions_file,
                    indent=4,
                )


builtin: Mapping[
    str,
    Callable[
        [
            Path,
            Mapping[str, Mapping[str, GenerateInputPackagesValue]],
        ],
        None,
    ],
] = {"versions": versions}
