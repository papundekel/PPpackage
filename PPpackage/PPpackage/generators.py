from collections.abc import Callable, Iterable, Mapping
from json import dumps as json_dumps
from pathlib import Path

from PPpackage_submanager.schemes import Product
from PPpackage_utils.utils import ensure_dir_exists


def versions(
    meta_products: Mapping[str, Iterable[Product]], destination_path: Path
) -> None:
    versions_path = destination_path / Path("versions")

    for manager, products in meta_products.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        for product in products:
            data = {"version": product.version, "product_id": product.product_id}

            with (manager_path / f"{product.name}.json").open("w") as file:
                file.write(json_dumps(data, indent=4))


builtin: Mapping[str, Callable[[Mapping[str, Iterable[Product]], Path], None]] = {
    "versions": versions
}
