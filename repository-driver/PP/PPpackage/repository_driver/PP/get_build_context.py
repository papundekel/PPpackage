from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    ProductInfos,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_build_context(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    raise Exception("Not implemented")
