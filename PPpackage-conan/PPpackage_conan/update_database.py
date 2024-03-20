from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import Mapping
from pathlib import Path

from PPpackage_submanager.exceptions import CommandException
from PPpackage_utils.utils import asubprocess_wait, ensure_dir_exists

from .settings import Settings
from .utils import State, make_conan_environment


async def update_database_impl(environment: Mapping[str, str], cache_path: Path):
    ensure_dir_exists(cache_path)

    process = await create_subprocess_exec(
        "conan",
        "cache",
        "check-integrity",
        "*",
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
        env=environment,
    )

    await asubprocess_wait(process, CommandException())


async def update_database(settings: Settings, state: State):
    environment = make_conan_environment(settings.cache_path)

    await update_database_impl(environment, settings.cache_path)
