from collections.abc import Callable, Iterable, Mapping
from io import BytesIO
from json import dumps as json_dumps
from pathlib import Path
from tarfile import TarFile

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import create_tar_directory, create_tar_file


def versions(
    meta_products: Mapping[str, Iterable[Product]],
) -> memoryview:
    io = BytesIO()

    versions_path = Path("versions")

    with TarFile(fileobj=io, mode="w") as tar:
        for manager, products in meta_products.items():
            manager_path = versions_path / manager

            create_tar_directory(tar, manager_path)

            for product in products:
                data = {"version": product.version, "product_id": product.product_id}

                with create_tar_file(
                    tar, manager_path / f"{product.name}.json"
                ) as file:
                    file.write(json_dumps(data, indent=4).encode())

    return io.getbuffer()


builtin: Mapping[str, Callable[[Mapping[str, Iterable[Product]]], memoryview]] = {
    "versions": versions
}
