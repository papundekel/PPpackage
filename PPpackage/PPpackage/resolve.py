from ast import parse
from asyncio import Lock, TaskGroup, create_subprocess_exec, taskgroups
from asyncio.subprocess import PIPE
from collections.abc import Iterable, Mapping, Set
from functools import partial, reduce
from hmac import new
from itertools import chain as itertools_chain
from itertools import product as itertools_product
from pathlib import Path
from sys import stderr
from typing import Any, Tuple

from PPpackage_utils.parse import Lockfile
from PPpackage_utils.utils import (
    MyException,
    Resolution,
    asubprocess_communicate,
    frozendict,
    json_dumps,
    json_loads,
)

from .parse import parse_resolutions
from .sub import resolve as PP_resolve


async def resolve_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> Set[Resolution]:
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

    resolutions_bytes = await asubprocess_communicate(
        process,
        f"Error in {manager}'s resolve.",
        resolve_input_json_bytes,
    )

    resolutions_string = resolutions_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}' resolve:", file=stderr)
        print(resolutions_string, file=stderr)

    resolutions = parse_resolutions(debug, json_loads(resolutions_string))

    return resolutions


async def resolve_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> Set[Resolution]:
    if manager == "PP":
        resolver = PP_resolve
    else:
        resolver = partial(resolve_external_manager, manager=manager)

    resolutions = await resolver(
        debug=debug, cache_path=cache_path, requirements=requirements, options=options
    )

    return resolutions


def merge_meta_requirements(a, b):
    return {
        manager: a.get(manager, frozenset()) | b.get(manager, frozenset())
        for manager in a.keys() | b.keys()
    }


async def resolve_iteration(
    debug: bool,
    cache_path: Path,
    meta_requirements_list: Iterable[Mapping[str, Set[Any]]],
    meta_options: Mapping[str, Any],
) -> Tuple[Set[Mapping[str, Lockfile]], Set[Mapping[str, Set[Any]]]]:
    lockfiles = set()
    requirements = set()

    for meta_requirements in meta_requirements_list:
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

        manager_resolutions = [
            {manager: resolution for manager, resolution in i}
            for i in itertools_product(
                *[
                    [(manager, resolution) for resolution in resolutions]
                    for manager, resolutions in meta_results.items()
                ]
            )
        ]

        for manager_resolution in manager_resolutions:
            meta_lockfile = {
                manager: resolution.lockfile
                for manager, resolution in manager_resolution.items()
            }

            new_meta_requirements = {
                manager: resolution.requirements
                for manager, resolution in manager_resolution.items()
            }

            merged_meta_requirements = reduce(
                merge_meta_requirements,
                new_meta_requirements.values(),
                meta_requirements,
            )

            if merged_meta_requirements == meta_requirements:
                lockfiles.add(frozendict(meta_lockfile))
            else:
                requirements.add(frozendict(merged_meta_requirements))

    return lockfiles, requirements


async def resolve(
    debug: bool,
    iteration_limit: int,
    cache_path: Path,
    meta_requirements: Mapping[str, Set[Any]],
    meta_options: Mapping[str, Any],
) -> Mapping[str, Lockfile]:
    iterations_done = 0

    meta_requirements_list = [meta_requirements]
    choices_of_meta_lockfiles = set()

    while len(meta_requirements_list) != 0:
        if iterations_done >= iteration_limit:
            raise MyException("Resolve iteration limit reached.")

        if debug:
            print(
                f"DEBUG PPpackage: resolve iteration with requirements: {json_dumps(meta_requirements_list)}",
                file=stderr,
            )

        lockfiles, meta_requirements_list = await resolve_iteration(
            debug, cache_path, meta_requirements_list, meta_options
        )

        choices_of_meta_lockfiles.update(lockfiles)

        iterations_done += 1

    if debug:
        print(
            f"DEBUG PPpackage: resolve choices of meta lockfiles:",
            file=stderr,
        )
        for meta_lockfile in choices_of_meta_lockfiles:
            print(f"DEBUG PPpackage: {json_dumps(meta_lockfile)}", file=stderr)

    # here is where the model is chosen
    meta_lockfile = next(x for x in choices_of_meta_lockfiles)

    return meta_lockfile
