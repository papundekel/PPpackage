from ast import parse
from asyncio import TaskGroup, create_subprocess_exec, taskgroups
from asyncio.subprocess import PIPE
from collections.abc import Iterable, Mapping, Set
from functools import partial, reduce
from hmac import new
from itertools import chain as itertools_chain
from itertools import product as itertools_product
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage_utils.parse import Lockfile
from PPpackage_utils.utils import (
    MyException,
    asubprocess_communicate,
    json_dumps,
    json_loads,
)

from .parse import parse_resolve_response
from .sub import resolve as PP_resolve


async def resolve_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> tuple[Set[Lockfile], Mapping[str, Set[Any]]]:
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

    response_bytes = await asubprocess_communicate(
        process,
        f"Error in {manager}'s resolve.",
        resolve_input_json_bytes,
    )

    response_string = response_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}' resolve:", file=stderr)
        print(response_string, file=stderr)

    lockfile_choices, new_requirements = parse_resolve_response(
        debug, json_loads(response_string)
    )

    return lockfile_choices, new_requirements


async def resolve_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> tuple[Set[Lockfile], Mapping[str, Set[Any]]]:
    if manager == "PP":
        resolver = PP_resolve
    else:
        resolver = partial(resolve_external_manager, manager=manager)

    lockfile_choices, new_requirements = await resolver(
        debug=debug, cache_path=cache_path, requirements=requirements, options=options
    )

    return lockfile_choices, new_requirements


def merge_meta_requirements(a, b):
    return {
        manager: a.get(manager, set()) | b.get(manager, set())
        for manager in a.keys() | b.keys()
    }


async def resolve(
    debug: bool,
    iteration_limit: int,
    cache_path: Path,
    meta_requirements: Mapping[str, Set[Any]],
    meta_options: Mapping[str, Any],
) -> Mapping[str, Mapping[str, str]]:
    iterations_done = 0

    while True:
        if iterations_done >= iteration_limit:
            raise MyException("Resolve iteration limit reached.")

        if debug:
            print(
                f"DEBUG PPpackage: resolve iteration with requirements: {meta_requirements}",
                file=stderr,
            )

        async with TaskGroup() as group:
            meta_tasks = {
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

        meta_results = {manager: task.result() for manager, task in meta_tasks.items()}

        meta_new_meta_requirements = [
            new_meta_requirements
            for _, (_, new_meta_requirements) in meta_results.items()
        ]

        merged_meta_requirements = reduce(
            merge_meta_requirements, meta_new_meta_requirements, meta_requirements
        )

        meta_lockfile_choices = {
            manager: lockfile_choices
            for manager, (lockfile_choices, _) in meta_results.items()
        }

        if merged_meta_requirements == meta_requirements:
            break

        meta_requirements = merged_meta_requirements

        iterations_done += 1

    choices_of_meta_lockfiles = [
        {manager: lockfile for manager, lockfile in i}
        for i in itertools_product(
            *[
                [(manager, lockfile) for lockfile in lockfile_choices]
                for manager, lockfile_choices in meta_lockfile_choices.items()
            ]
        )
    ]

    # here is where the model is chosen
    meta_lockfile = choices_of_meta_lockfiles[0]

    return meta_lockfile
