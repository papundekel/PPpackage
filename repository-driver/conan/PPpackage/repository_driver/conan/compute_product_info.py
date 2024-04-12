from collections.abc import Mapping
from typing import Any

from .schemes import DriverParameters, RepositoryParameters


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Mapping[str, Any],
    package: str,
    product_infos: Mapping[str, tuple[Any]],
) -> Any:
    return None
