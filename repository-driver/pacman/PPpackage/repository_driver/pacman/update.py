from shutil import move

from pyalpm import Handle

from PPpackage.utils.utils import TemporaryDirectory

from .schemes import DriverParameters, RepositoryParameters
from .utils import Database


async def update(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    with Database(repository_parameters) as database:
        if "epoch" in database:
            epoch = database["epoch"]
        else:
            epoch = 0

        with TemporaryDirectory() as root_directory_path:
            handle = Handle(
                str(root_directory_path), str(repository_parameters.database_path)
            )

            alpm_database = handle.register_syncdb(repository_parameters.repository, 0)

            alpm_database.servers = repository_parameters.mirrorlist

            alpm_database.update(True)

            sync_database_path = repository_parameters.database_path / "sync"

            move(
                sync_database_path / f"{repository_parameters.repository}.db",
                sync_database_path / "database.db",
            )

        database["epoch"] = epoch + 1
        database.commit()
