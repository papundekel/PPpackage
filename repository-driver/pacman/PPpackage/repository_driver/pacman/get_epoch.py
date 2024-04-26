from .epoch import get
from .schemes import DriverParameters, RepositoryParameters


async def get_epoch(
    driver_parameters: DriverParameters, repository_parameters: RepositoryParameters
) -> str:
    return get(repository_parameters.database_path / "database.sqlite")
