from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from pathlib import Path
from sys import stderr

from PPpackage_utils.utils import (
    asubprocess_wait,
    debug_redirect_stderr,
    debug_redirect_stdout,
    ensure_dir_exists,
    fakeroot,
)

from .utils import get_cache_paths


async def update_database(debug: bool, cache_path: Path) -> None:
    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    async with fakeroot(debug) as environment:
        process = create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--sync",
            "--refresh",
            stdin=DEVNULL,
            stdout=debug_redirect_stdout(debug),
            stderr=debug_redirect_stderr(debug),
            env=environment,
        )

        await asubprocess_wait(await process, "Error in `pacman -Sy`")
