from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from pathlib import Path
from sys import stderr

from PPpackage_utils.utils import asubprocess_communicate, ensure_dir_exists, fakeroot

from .utils import get_cache_paths


async def update_database(cache_path: Path) -> None:
    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    async with fakeroot() as environment:
        process = create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--sync",
            "--refresh",
            stdin=DEVNULL,
            stdout=stderr,
            stderr=None,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `pacman -Sy`")
