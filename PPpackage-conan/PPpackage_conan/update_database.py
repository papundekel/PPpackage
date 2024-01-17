from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import Mapping
from sys import stderr

from PPpackage_submanager.exceptions import CommandException
from PPpackage_utils.utils import asubprocess_wait

from .settings import Settings
from .utils import State, make_conan_environment


async def update_database_impl(environment: Mapping[str, str]):
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

    await update_database_impl(environment)
