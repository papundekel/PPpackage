from asyncio import TaskGroup
from collections.abc import Iterable, Mapping
from sys import stderr

from .submanager import Submanager


async def update_database(
    submanagers: Mapping[str, Submanager],
    submanager_names: Iterable[str],
) -> None:
    stderr.write("Updating databases...\n")

    async with TaskGroup() as group:
        for submanager_name in submanager_names:
            submanager = submanagers[submanager_name]
            group.create_task(submanager.update_database())
