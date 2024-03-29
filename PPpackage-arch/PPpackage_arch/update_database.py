from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL

from PPpackage_submanager.exceptions import CommandException
from PPpackage_utils.utils import asubprocess_wait, ensure_dir_exists, fakeroot

from .settings import Settings
from .utils import get_cache_paths


async def update_database(settings: Settings, state: None):
    database_path, _ = get_cache_paths(settings.cache_path)

    ensure_dir_exists(database_path)

    async with fakeroot() as environment:
        process = await create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--sync",
            "--refresh",
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=None,
            env=environment,
        )

        await asubprocess_wait(process, CommandException)
