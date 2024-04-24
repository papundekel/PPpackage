from shutil import move

from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters


async def update(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    with TemporaryDirectory() as root_directory_path:
        handle = Handle(
            str(root_directory_path), str(repository_parameters.database_path)
        )

        database = handle.register_syncdb(repository_parameters.repository, 0)

        database.servers = repository_parameters.mirrorlist

        database.update(True)

        sync_database_path = repository_parameters.database_path / "sync"

        move(
            sync_database_path / f"{repository_parameters.repository}.db",
            sync_database_path / "database.db",
        )
