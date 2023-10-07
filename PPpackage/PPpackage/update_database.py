from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import Iterable
from functools import partial
from pathlib import Path

from PPpackage_utils.utils import asubprocess_communicate

from .sub import update_database as PP_update_database


async def update_database_external_manager(debug: bool, manager: str, cache_path: Path):
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "update-database",
        str(cache_path),
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=None,
    )

    await asubprocess_communicate(
        process,
        f"Error in {manager}'s update-database.",
    )


async def update_database_manager(debug: bool, manager: str, cache_path: Path):
    if manager == "PP":
        updater = PP_update_database
    else:
        updater = partial(
            update_database_external_manager,
            manager=manager,
        )

    await updater(debug=debug, cache_path=cache_path)


async def update_database(
    debug: bool, managers: Iterable[str], cache_path: Path
) -> None:
    async with TaskGroup() as group:
        for manager in managers:
            group.create_task(update_database_manager(debug, manager, cache_path))
