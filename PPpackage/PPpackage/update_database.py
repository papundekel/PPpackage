from asyncio import StreamReader, StreamWriter, TaskGroup
from collections.abc import Iterable, Mapping, MutableMapping
from pathlib import Path
from sys import stderr

from PPpackage_utils.parse import dump_one, load_one
from PPpackage_utils.utils import SubmanagerCommand

from .utils import SubmanagerCommandFailure, open_submanager


async def update_database_manager(
    debug: bool,
    submanager_socket_paths: Mapping[str, Path],
    connections: MutableMapping[str, tuple[StreamReader, StreamWriter]],
    manager: str,
):
    stderr.write(f"Updating {manager} database...\n")

    reader, writer = await open_submanager(
        manager, submanager_socket_paths, connections
    )

    await dump_one(debug, writer, SubmanagerCommand.UPDATE_DATABASE)

    success = await load_one(debug, reader, bool)

    if not success:
        raise SubmanagerCommandFailure(f"{manager} failed to update its database.")


async def update_database(
    debug: bool,
    submanager_socket_paths: Mapping[str, Path],
    connections: MutableMapping[str, tuple[StreamReader, StreamWriter]],
    managers: Iterable[str],
) -> None:
    stderr.write("Updating databases...\n")

    async with TaskGroup() as group:
        for manager in managers:
            group.create_task(
                update_database_manager(
                    debug, submanager_socket_paths, connections, manager
                )
            )
