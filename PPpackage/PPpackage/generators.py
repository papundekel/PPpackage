from collections.abc import Callable, Mapping
from json import dump as json_dump
from pathlib import Path

from PPpackage_utils.parse import Products
from PPpackage_utils.utils import ensure_dir_exists


def versions(
    generators_path: Path,
    meta_products: Mapping[str, Products],
) -> None:
    versions_path = generators_path / "versions"

    for manager, products in meta_products.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        for package_name, product_base in products.items():
            with (manager_path / f"{package_name}.json").open("w") as versions_file:
                json_dump(
                    {
                        "version": product_base.version,
                        "product_id": product_base.product_id,
                    },
                    versions_file,
                    indent=4,
                )


builtin: Mapping[
    str,
    Callable[
        [
            Path,
            Mapping[str, Products],
        ],
        None,
    ],
] = {"versions": versions}
