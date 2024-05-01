from itertools import chain

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)
from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import PREFIX, parse_package_name, strip_version


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb("database", 0)

        package = database.get_pkg(name)

        if package is None:
            raise Exception(f"Invalid package: {full_package_name}")

        if package.version != version:
            raise Exception(f"Invalid package: {full_package_name}")

        return {
            f"pacman-{strip_version(provide)}": {"version": f"{version}"}
            for provide in chain([name], package.provides)
        }
