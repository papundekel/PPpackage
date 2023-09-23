#!/usr/bin/env python

import asyncio
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence, Set
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PPpackage_utils import (
    AsyncTyper,
    MyException,
    SetEncoder,
    asubprocess_communicate,
    check_dict_format,
    ensure_dir_exists,
    parse_generators,
)


def check_requirements(input: Any) -> Mapping[str, Iterable[Any]]:
    if type(input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")

    return input


def parse_requirements(input: Any) -> Mapping[str, Iterable[Any]]:
    input_checked = check_requirements(input)

    requirements = input_checked

    return requirements


def merge_lockfiles(
    versions: Mapping[str, str], product_ids: Mapping[str, str]
) -> Mapping[str, Mapping[str, str]]:
    return {
        package: {"version": versions[package], "product_id": product_ids[package]}
        for package in versions
        if package in product_ids
    }


def get_manager_command_path(managers_path: Path, manager: str) -> Path:
    return managers_path.absolute() / f"PPpackage_{manager}.py"


def check_options(input: Any) -> Mapping[str, Any]:
    if type(input) is not dict:
        raise MyException("Invalid options format.")

    for manager_input, options_input in input.items():
        if type(manager_input) is not str:
            raise MyException("Invalid options format.")

        # TODO: rethink
        if type(options_input) is not dict:
            raise MyException("Invalid options format.")

    return input


def parse_options(input: Any) -> Mapping[str, Any]:
    input_checked = check_options(input)

    options = input_checked

    return options


def parse_input(
    input: Any,
) -> tuple[Mapping[str, Iterable[Any]], Mapping[str, Any], Set[str]]:
    input_checked = check_dict_format(
        input,
        {"requirements", "options", "generators"},
        set(),
        "Invalid input format.",
    )

    requirements = parse_requirements(input_checked["requirements"])
    options = parse_options(input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return requirements, options, generators


def generator_versions(
    generators_path: Path,
    manager_versions_dict: Mapping[str, Mapping[str, str]],
    manager_product_ids: Mapping[str, Mapping[str, str]],
) -> None:
    versions_path = generators_path / "versions"

    for manager, versions in manager_versions_dict.items():
        manager_path = versions_path / manager

        ensure_dir_exists(manager_path)

        product_ids = manager_product_ids[manager]

        for package, version in versions.items():
            product_id = product_ids[package]

            with open(manager_path / f"{package}.json", "w") as versions_file:
                json.dump(
                    {"version": version, "product_id": product_id},
                    versions_file,
                    indent=4,
                )


builtin_generators: Mapping[
    str,
    Callable[
        [Path, Mapping[str, Mapping[str, str]], Mapping[str, Mapping[str, str]]], None
    ],
] = {"versions": generator_versions}


@contextmanager
def TemporaryDirectory():
    with tempfile.TemporaryDirectory() as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


@contextmanager
def TemporaryPipe():
    with TemporaryDirectory() as dir_path:
        pipe_path = dir_path / "pipe"

        os.mkfifo(pipe_path)

        yield pipe_path


def read_string(input: io.TextIOBase) -> str | None:
    length = int(input.readline().strip())

    if length < 0:
        return None

    string = input.read(length)
    return string


def read_strings(input: io.TextIOBase) -> Iterable[str]:
    while True:
        string = read_string(input)

        if string is None:
            break

        yield string


@contextmanager
def edit_json_file(path: Path, debug: bool) -> Any:
    with path.open("r+") as file:
        data = json.load(file)

        yield data

        file.seek(0)
        file.truncate()

        json.dump(data, file, indent=4 if debug else None)


async def install_manager(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager_product_ids_dict: Mapping[str, Mapping[str, str]],
    destination_path: Path,
    manager: str,
    versions: Mapping[str, str],
    bundle_dir_path: Path,
) -> None:
    manager_command_path = get_manager_command_path(managers_path, manager)

    with TemporaryPipe() as pipe_from_sub_path, TemporaryPipe() as pipe_to_sub_path:
        if debug:
            print(
                f"DEBUG PPpackage: {manager} pipe_from_sub_path: {pipe_from_sub_path}, pipe_to_sub_path: {pipe_to_sub_path}",
                file=sys.stderr,
            )

        process_creation = asyncio.create_subprocess_exec(
            str(manager_command_path),
            "--debug" if debug else "--no-debug",
            "install",
            str(cache_path),
            str(destination_path),
            str(pipe_from_sub_path),
            str(pipe_to_sub_path),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )

        product_ids = manager_product_ids_dict[manager]

        products = merge_lockfiles(versions, product_ids)

        indent = 4 if debug else None

        products_json = json.dumps(products, indent=indent)

        if debug:
            print(f"DEBUG PPpackage: sending to {manager}'s install:", file=sys.stderr)
            print(products_json, file=sys.stderr)

        products_json_bytes = products_json.encode("ascii")

        process = await process_creation

        process.stdin.write(products_json_bytes)
        process.stdin.close()
        await process.stdin.wait_closed()

        with open(pipe_from_sub_path, "r", encoding="ascii") as pipe_from_sub:
            with open(pipe_to_sub_path, "w", encoding="ascii") as pipe_to_sub:
                while True:
                    header = pipe_from_sub.readline().strip()

                    if header == "END":
                        break
                    elif header == "COMMAND":
                        command = read_string(pipe_from_sub)
                        args = list(read_strings(pipe_from_sub))
                        print(
                            f"{manager} requested hook `{command} {args}`.",
                            file=sys.stderr,
                        )

                        with TemporaryPipe() as pipe_hook_path:
                            pipe_hook_path_str = str(pipe_hook_path)

                            pipe_to_sub.write(f"{len(pipe_hook_path_str)}\n")
                            pipe_to_sub.write(pipe_hook_path_str)

                            pipe_to_sub.flush()

                            with open(
                                pipe_hook_path, "r", encoding="ascii"
                            ) as pipe_hook:
                                with edit_json_file(
                                    bundle_dir_path / "config.json", debug
                                ) as config:
                                    config["process"]["args"] = [command, *args[1:]]

                                process_creation = asyncio.create_subprocess_exec(
                                    "runc",
                                    "run",
                                    "--bundle",
                                    str(bundle_dir_path),
                                    "PPpackage-container",
                                    stdin=pipe_hook,
                                    stderr=None,
                                    stdout=sys.stderr,
                                )

                                await asubprocess_communicate(
                                    await process_creation, "Error in `runc run`.", None
                                )
                    else:
                        raise MyException(
                            f"Invalid hook header from {manager} `{header}`."
                        )

        await asubprocess_communicate(
            process,
            f"Error in {manager}'s install.",
            None,
        )


async def resolve_manager(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager: str,
    requirements: Iterable[Any],
    manager_options_dict: Mapping[str, Any],
    manager_lockfiles: MutableMapping[str, Iterable[Any]],
) -> None:
    manager_command_path = get_manager_command_path(managers_path, manager)

    process = asyncio.create_subprocess_exec(
        str(manager_command_path),
        "--debug" if debug else "--no-debug",
        "resolve",
        str(cache_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    options = manager_options_dict.get(manager)

    indent = 4 if debug else None

    resolve_input_json = json.dumps(
        {
            "requirements": requirements,
            "options": options,
        },
        indent=indent,
    )

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s resolve:", file=sys.stderr)
        print(resolve_input_json, file=sys.stderr)

    resolve_input_json_bytes = resolve_input_json.encode("ascii")

    lockfiles_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s resolve.",
        resolve_input_json_bytes,
    )

    lockfiles_json = lockfiles_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}' resolve:", file=sys.stderr)
        print(lockfiles_json, file=sys.stderr)

    lockfiles = json.loads(lockfiles_json)

    manager_lockfiles[manager] = lockfiles


async def fetch_manager(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager: str,
    versions: Mapping[str, str],
    manager_options_dict: Mapping[str, Any],
    generators: Iterable[str],
    generators_path: Path,
    manager_product_ids_dict: MutableMapping[str, Mapping[str, str]],
) -> None:
    manager_command_path = get_manager_command_path(managers_path, manager)

    process = asyncio.create_subprocess_exec(
        str(manager_command_path),
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        str(generators_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    options = manager_options_dict.get(manager)

    indent = 4 if debug else None

    fetch_input_json = json.dumps(
        {
            "lockfile": versions,
            "options": options,
            "generators": generators - builtin_generators.keys(),
        },
        cls=SetEncoder,
        indent=indent,
    )

    if debug:
        print(f"DEBUG PPpackage: sending to {manager}'s fetch:", file=sys.stderr)
        print(fetch_input_json, file=sys.stderr)

    fetch_input_json_bytes = fetch_input_json.encode("ascii")

    product_ids_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s fetch.",
        fetch_input_json_bytes,
    )

    product_ids_json = product_ids_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}'s fetch:", file=sys.stderr)
        print(product_ids_json, file=sys.stderr)

    product_ids = json.loads(product_ids_json)

    manager_product_ids_dict[manager] = product_ids


async def resolve(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager_requirements: Mapping[str, Iterable[Any]],
    manager_options_dict: Mapping[str, Any],
) -> Mapping[str, Mapping[str, str]]:
    manager_lockfiles: MutableMapping[str, Iterable[Mapping[str, str]]] = {}

    async with asyncio.TaskGroup() as group:
        for manager, requirements in manager_requirements.items():
            group.create_task(
                resolve_manager(
                    debug,
                    managers_path,
                    cache_path,
                    manager,
                    requirements,
                    manager_options_dict,
                    manager_lockfiles,
                )
            )

    lockfiles: Sequence[Mapping[str, Mapping[str, str]]] = [
        {manager: lockfile for manager, lockfile in i}
        for i in itertools.product(
            *[
                [(manager, lockfile) for lockfile in lockfiles]
                for manager, lockfiles in manager_lockfiles.items()
            ]
        )
    ]

    lockfile = lockfiles[0]

    return lockfile


async def fetch(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager_versions_dict: Mapping[str, Mapping[str, str]],
    manager_options_dict: Mapping[str, Any],
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, Mapping[str, str]]:
    manager_product_ids_dict: MutableMapping[str, Mapping[str, str]] = {}

    async with asyncio.TaskGroup() as group:
        for manager, versions in manager_versions_dict.items():
            group.create_task(
                fetch_manager(
                    debug,
                    managers_path,
                    cache_path,
                    manager,
                    versions,
                    manager_options_dict,
                    generators,
                    generators_path,
                    manager_product_ids_dict,
                )
            )

    for generator in generators & builtin_generators.keys():
        builtin_generators[generator](
            generators_path, manager_versions_dict, manager_product_ids_dict
        )

    return manager_product_ids_dict


async def install(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager_versions_dict: Mapping[str, Mapping[str, str]],
    manager_product_ids_dict: Mapping[str, Mapping[str, str]],
    destination_path: Path,
) -> None:
    with TemporaryDirectory() as bundle_dir_path:
        (bundle_dir_path / "rootfs").mkdir()

        process_creation = asyncio.create_subprocess_exec(
            "runc",
            "spec",
            "--rootless",
            "--bundle",
            str(bundle_dir_path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )

        await asubprocess_communicate(
            await process_creation, "Error in `runc spec`.", None
        )

        with edit_json_file(bundle_dir_path / "config.json", debug) as config:
            config["process"]["terminal"] = False
            config["root"]["path"] = str(destination_path.absolute())
            config["root"]["readonly"] = False

        for manager, versions in manager_versions_dict.items():
            await install_manager(
                debug,
                managers_path,
                cache_path,
                manager_product_ids_dict,
                destination_path,
                manager,
                versions,
                bundle_dir_path,
            )


app = AsyncTyper()


@app.command()
async def main(
    managers_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    debug: bool = False,
) -> None:
    requirements_generators_input = json.load(sys.stdin)

    requirements, options, generators = parse_input(requirements_generators_input)

    versions = await resolve(debug, managers_path, cache_path, requirements, options)

    product_ids = await fetch(
        debug, managers_path, cache_path, versions, options, generators, generators_path
    )

    await install(
        debug, managers_path, cache_path, versions, product_ids, destination_path
    )


if __name__ == "__main__":
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"PPpackage: {e}", file=sys.stderr)
        sys.exit(1)
