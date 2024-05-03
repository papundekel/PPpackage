from PPpackage.repository_driver.interface.schemes import ProductInfo, ProductInfos

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def compute_product_info(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
    build_product_infos: ProductInfos,
    runtime_product_infos: ProductInfos,
) -> ProductInfo:
    return {}
