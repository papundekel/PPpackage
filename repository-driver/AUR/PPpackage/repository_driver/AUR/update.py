from gzip import open as gzip_open

from anysqlite import connect as sqlite_connect
from hishel import AsyncCacheClient as HTTPClient
from hishel import AsyncSQLiteStorage
from sqlitedict import SqliteDict

from PPpackage.utils.utils import TemporaryDirectory
from PPpackage.utils.validation import validate_json

from .epoch import update as update_epoch
from .schemes import AURPackage, DriverParameters, RepositoryParameters


async def update(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    database_path = repository_parameters.database_path
    database_path.mkdir(parents=True, exist_ok=True)

    async with HTTPClient(
        http2=True,
        storage=AsyncSQLiteStorage(
            connection=await sqlite_connect(database_path / "http-cache.sqlite")
        ),
    ) as client:
        with TemporaryDirectory() as download_directory_path:
            async with client.stream(
                "GET", "https://aur.archlinux.org/packages-meta-ext-v1.json.gz"
            ) as response:
                gunzipped_packages = download_directory_path / "packages.json.gz"

                with gunzipped_packages.open("wb") as file:
                    async for chunk in response.aiter_raw():
                        file.write(chunk)

            with gzip_open(gunzipped_packages, "rb") as file:
                packages_json = file.read()

    with SqliteDict(
        database_path / "database.sqlite", tablename="packages"
    ) as database:
        for package in validate_json(list[AURPackage], packages_json):
            database[package.Name] = package
        database.commit()

    update_epoch(database_path / "database.sqlite")
