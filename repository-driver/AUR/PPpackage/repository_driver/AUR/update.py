from gzip import open as gzip_open

from aiosqlite import Connection
from anysqlite import connect as sqlite_connect
from hishel import AsyncCacheClient as HTTPClient
from hishel import AsyncSQLiteStorage

from PPpackage.utils.file import TemporaryDirectory
from PPpackage.utils.json.validate import validate_json

from .epoch import update as update_epoch
from .schemes import AURPackage, DriverParameters, RepositoryParameters
from .state import State
from .utils import transaction


async def create_database_epoch(connection: Connection):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS epochs
            (epoch TEXT PRIMARY KEY)
        """
    )

    await connection.execute("DELETE FROM epochs")

    await connection.execute("INSERT INTO epochs VALUES (?)", ("",))


async def create_database_packages(
    connection: Connection, insert_packages: list[tuple[str, str]]
):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packages
            (name TEXT PRIMARY KEY,
            version TEXT NOT NULL)
        """
    )

    await connection.execute("DELETE FROM packages")

    await connection.executemany("INSERT INTO packages VALUES (?, ?)", insert_packages)


async def create_database_provides(
    connection: Connection, insert_package_provides: list[tuple[str, str]]
):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS provides
            (name TEXT,
            provide TEXT NOT NULL,
            FOREIGN KEY (name) REFERENCES packages(name) ON DELETE CASCADE,
            UNIQUE (name, provide))
        """
    )

    await connection.execute("DELETE FROM provides")

    await connection.executemany(
        "INSERT INTO provides VALUES (?, ?)", insert_package_provides
    )


async def create_database_conflicts(
    connection: Connection, insert_package_conflicts: list[tuple[str, str]]
):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conflicts
            (name TEXT,
            conflict TEXT NOT NULL,
            FOREIGN KEY (name) REFERENCES packages(name) ON DELETE CASCADE,
            UNIQUE (name, conflict))
        """
    )

    await connection.execute("DELETE FROM conflicts")

    await connection.executemany(
        "INSERT INTO conflicts VALUES (?, ?)", insert_package_conflicts
    )


async def create_database_runtime_dependencies(
    connection: Connection, insert_package_runtime_dependencies: list[tuple[str, str]]
):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dependencies
            (name TEXT,
            dependency TEXT NOT NULL,
            FOREIGN KEY (name) REFERENCES packages(name) ON DELETE CASCADE,
            UNIQUE (name, dependency))
        """
    )

    await connection.execute("DELETE FROM runtime_dependencies")

    await connection.executemany(
        "INSERT INTO runtime_dependencies VALUES (?, ?)",
        insert_package_runtime_dependencies,
    )


async def create_database_build_dependencies(
    connection: Connection, insert_package_build_dependencies: list[tuple[str, str]]
):
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS build_dependencies
            (name TEXT,
            dependency TEXT NOT NULL,
            FOREIGN KEY (name) REFERENCES packages(name) ON DELETE CASCADE,
            UNIQUE (name, dependency))
        """
    )

    await connection.execute("DELETE FROM build_dependencies")

    await connection.executemany(
        "INSERT INTO build_dependencies VALUES (?, ?)",
        insert_package_build_dependencies,
    )


async def update(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    database_path = repository_parameters.database_path
    database_path.mkdir(parents=True, exist_ok=True)

    async with HTTPClient(
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

    insert_packages = []
    insert_package_provides = []
    insert_package_conflicts = []
    insert_package_runtime_dependencies = []
    insert_package_build_dependencies = []

    for package in validate_json(list[AURPackage], packages_json):
        insert_packages.append((package.Name, package.Version))
        insert_package_provides.extend(
            (package.Name, provide) for provide in package.Provides
        )
        insert_package_conflicts.extend(
            (package.Name, conflict) for conflict in package.Conflicts
        )
        insert_package_runtime_dependencies.extend(
            (package.Name, dependency) for dependency in package.Depends
        )
        insert_package_build_dependencies.extend(
            (package.Name, dependency) for dependency in package.MakeDepends
        )

    connection = state.connection

    async with transaction(connection):
        await create_database_epoch(connection)

        await update_epoch(connection)

        await create_database_packages(connection, insert_packages)
        await create_database_provides(connection, insert_package_provides)
        await create_database_conflicts(connection, insert_package_conflicts)
        await create_database_runtime_dependencies(
            connection, insert_package_runtime_dependencies
        )
        await create_database_build_dependencies(
            connection, insert_package_build_dependencies
        )
