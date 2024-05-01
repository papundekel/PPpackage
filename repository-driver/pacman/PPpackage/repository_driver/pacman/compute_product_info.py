from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)

from .schemes import DriverParameters, RepositoryParameters
from .utils import PREFIX, parse_package_name


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    return {f"pacman-{name}": {"version": f"{version}"}}
