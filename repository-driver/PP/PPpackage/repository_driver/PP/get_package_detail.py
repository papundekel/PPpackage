from PPpackage.repository_driver.interface.schemes import PackageDetail

from .schemes import DriverParameters, RepositoryParameters
from .state import State


async def get_package_detail(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    package: str,
) -> PackageDetail | None:
    return None
