from .epoch import update as update_epoch
from .schemes import DriverParameters, RepositoryParameters


async def update(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    with update_epoch(repository_parameters.database_path / "database.sqlite"):
        pass
