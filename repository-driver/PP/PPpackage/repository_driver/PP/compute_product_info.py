from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def compute_product_info(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    return {}
