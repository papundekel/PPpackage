from collections.abc import Mapping
from typing import Any

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: ConanOptions,
    package: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    return {}
