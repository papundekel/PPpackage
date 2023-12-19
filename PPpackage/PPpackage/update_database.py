from asyncio import TaskGroup
from collections.abc import Iterable
from sys import stderr

from PPpackage_utils.parse import load_one
from PPpackage_utils.utils import SubmanagerCommand

from .utils import Connections, SubmanagerCommandFailure


async def update_database_manager(debug: bool, connections: Connections, manager: str):
    stderr.write(f"Updating {manager} database...\n")

    async with connections.connect(
        debug, manager, SubmanagerCommand.UPDATE_DATABASE
    ) as (reader, _):
        success = await load_one(debug, reader, bool)

        if not success:
            raise SubmanagerCommandFailure(f"{manager} failed to update its database.")


async def update_database(
    debug: bool,
    connections: Connections,
    managers: Iterable[str],
) -> None:
    stderr.write("Updating databases...\n")

    async with TaskGroup() as group:
        for manager in managers:
            group.create_task(update_database_manager(debug, connections, manager))
