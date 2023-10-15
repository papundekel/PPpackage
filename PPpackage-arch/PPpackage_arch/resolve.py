from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Generator, Set
from pathlib import Path
from re import compile as re_compile

from PPpackage_utils.utils import (
    MyException,
    Resolution,
    asubprocess_communicate,
    frozendict,
)

from .update_database import update_database
from .utils import get_cache_paths


async def resolve_requirement_invoke(database_path: Path, requirement: str) -> bytes:
    process = await create_subprocess_exec(
        "pactree",
        "--dbpath",
        str(database_path),
        "--sync",
        requirement,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(process, "Error in `pactree`.")

    return stdout


regex_package_name = re_compile(r"[a-zA-Z0-9\-@._+]+")


def resolve_requirement_parse(stdout: bytes) -> Generator[str, None, None]:
    for line in stdout.decode("utf-8").splitlines():
        match = regex_package_name.search(line)

        if match is None:
            raise MyException("Invalid pactree output.")

        dependency = match.group()
        yield dependency


async def resolve(
    cache_path: Path, requirements: Set[str], options: None
) -> Set[Resolution]:
    database_path, _ = get_cache_paths(cache_path)

    if not database_path.exists():
        await update_database(cache_path)

    async with TaskGroup() as group:
        tasks = [
            group.create_task(resolve_requirement_invoke(database_path, requirement))
            for requirement in requirements
        ]

    dependencies = {
        dependency
        for task in tasks
        for dependency in resolve_requirement_parse(task.result())
    }

    process = create_subprocess_exec(
        "pacinfo",
        "--dbpath",
        str(database_path),
        "--short",
        *dependencies,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacinfo`.")

    lockfile = frozendict(
        {
            (split_line := line.split())[0]
            .split("/")[-1]: split_line[1]
            .rsplit("-", 1)[0]
            for line in stdout.decode("ascii").splitlines()
            if not line.startswith(" ")
        }
    )

    return frozenset([Resolution(lockfile, frozendict())])
