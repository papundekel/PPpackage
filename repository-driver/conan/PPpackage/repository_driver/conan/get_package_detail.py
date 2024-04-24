from pydantic import AnyUrl

from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from .schemes import ConanOptions, DriverParameters, RepositoryParameters


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: ConanOptions,
    package: str,
) -> PackageDetail | None:
    return None
