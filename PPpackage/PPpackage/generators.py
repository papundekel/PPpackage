from collections.abc import Callable, Mapping, Set
from json import dump as json_dump
from pathlib import Path

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import ensure_dir_exists


def versions(
    generators_path: Path,
    meta_products: Mapping[str, Set[Product]],
) -> None:
    versions_path = generators_path / "versions"

    for manager, products in meta_products.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        for product in products:
            with (manager_path / f"{product.name}.json").open("w") as versions_file:
                json_dump(
                    {"version": product.version, "product_id": product.product_id},
                    versions_file,
                    indent=4,
                )


builtin: Mapping[
    str,
    Callable[
        [
            Path,
            Mapping[str, Set[Product]],
        ],
        None,
    ],
] = {"versions": versions}
