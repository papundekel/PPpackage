from .schemes import DriverParameters, RepositoryParameters
from .utils import Database


async def get_epoch(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> str:
    with Database(repository_parameters) as database:
        return str(database["epoch"])
