from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)

from .schemes import DriverParameters, RepositoryParameters


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    return {}
