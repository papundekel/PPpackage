from .schemes import DriverParameters, RepositoryParameters


async def get_epoch(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> str:
    return "0"
