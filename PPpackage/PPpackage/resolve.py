from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Iterable, Mapping
from functools import partial
from itertools import product as itertools_product
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage_utils.utils import asubprocess_communicate, json_dumps, json_loads

from .sub import resolve as PP_resolve


async def resolve_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Iterable[Any],
    options: Mapping[str, Any] | None,
) -> Iterable[Mapping[str, str]]:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "resolve",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    indent = 4 if debug else None

    resolve_input_json = json_dumps(
        {
            "requirements": requirements,
            "options": options,
        },
        indent=indent,
    )

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s resolve:", file=stderr)
        print(resolve_input_json, file=stderr)

    resolve_input_json_bytes = resolve_input_json.encode("ascii")

    lockfiles_json_bytes = await asubprocess_communicate(
        process,
        f"Error in {manager}'s resolve.",
        resolve_input_json_bytes,
    )

    lockfiles_json = lockfiles_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}' resolve:", file=stderr)
        print(lockfiles_json, file=stderr)

    lockfiles = json_loads(lockfiles_json)

    return lockfiles


async def resolve_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Iterable[Any],
    options: Mapping[str, Any] | None,
) -> Iterable[Mapping[str, str]]:
    if manager == "PP":
        resolver = PP_resolve
    else:
        resolver = partial(resolve_external_manager, manager=manager)

    lockfiles = await resolver(
        debug=debug, cache_path=cache_path, requirements=requirements, options=options
    )

    return lockfiles


async def resolve(
    debug: bool,
    cache_path: Path,
    meta_requirements: Mapping[str, Iterable[Any]],
    meta_options: Mapping[str, Any],
) -> Mapping[str, Mapping[str, str]]:
    async with TaskGroup() as group:
        meta_lockfiles_tasks = {
            manager: group.create_task(
                resolve_manager(
                    debug,
                    manager,
                    cache_path,
                    requirements,
                    meta_options.get(manager),
                )
            )
            for manager, requirements in meta_requirements.items()
        }

    meta_lockfiles = [
        {manager: lockfile for manager, lockfile in i}
        for i in itertools_product(
            *[
                [(manager, lockfile) for lockfile in lockfiles_task.result()]
                for manager, lockfiles_task in meta_lockfiles_tasks.items()
            ]
        )
    ]

    # here is where the model is chosen
    meta_lockfile = meta_lockfiles[0]

    return meta_lockfile
