#!/usr/bin/env python

import itertools
import json
import random
from asyncio import (
    StreamReader,
    StreamWriter,
    TaskGroup,
    create_subprocess_exec,
    open_unix_connection,
)
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence, Set
from contextlib import asynccontextmanager, contextmanager
from functools import partial
from io import TextIOWrapper
from os import mkfifo
from pathlib import Path
from sys import stderr, stdin
from typing import Any

import PPpackage_sub
from PPpackage_utils import (
    AsyncTyper,
    MyException,
    SetEncoder,
    TemporaryDirectory,
    asubprocess_communicate,
    check_dict_format,
    ensure_dir_exists,
    parse_generators,
    pipe_read_line,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
    stream_read_int,
    stream_read_line,
    stream_write_line,
    stream_write_string,
    stream_write_strings,
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

            with (manager_path / f"{package}.json").open("w") as versions_file:
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
def TemporaryPipe(dir=None):
    with TemporaryDirectory(dir) as dir_path:
        pipe_path = dir_path / "pipe"

        mkfifo(pipe_path)

        yield pipe_path


async def install_manager_command(
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
):
    stream_write_line(daemon_writer, "COMMAND")
    stream_write_string(daemon_writer, str(destination_relative_path))
    stream_write_string(daemon_writer, pipe_read_string(pipe_from_sub))
    stream_write_strings(daemon_writer, pipe_read_strings(pipe_from_sub))

    with TemporaryPipe(daemon_workdir_path) as pipe_hook_path:
        pipe_write_string(pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        stream_write_string(
            daemon_writer, str(pipe_hook_path.relative_to(daemon_workdir_path))
        )

        await daemon_writer.drain()

        return_value = await stream_read_int(daemon_reader)

        pipe_write_int(pipe_to_sub, return_value)
        pipe_to_sub.flush()


async def install_external_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    manager_command_path = get_manager_command_path(managers_path, manager)

    with TemporaryPipe() as pipe_from_sub_path, TemporaryPipe() as pipe_to_sub_path:
        if debug:
            print(
                f"DEBUG PPpackage: {manager} pipe_from_sub_path: {pipe_from_sub_path}, pipe_to_sub_path: {pipe_to_sub_path}",
                file=stderr,
            )

        process_creation = create_subprocess_exec(
            str(manager_command_path),
            "--debug" if debug else "--no-debug",
            "install",
            str(cache_path),
            str(daemon_workdir_path / destination_relative_path),
            str(pipe_from_sub_path),
            str(pipe_to_sub_path),
            stdin=PIPE,
            stdout=DEVNULL,
            stderr=None,
        )

        products = merge_lockfiles(versions, product_ids)

        indent = 4 if debug else None

        products_json = json.dumps(products, indent=indent)

        if debug:
            print(f"DEBUG PPpackage: sending to {manager}'s install:", file=stderr)
            print(products_json, file=stderr)

        products_json_bytes = products_json.encode("ascii")

        process = await process_creation

        if process.stdin is None:
            raise MyException(f"Error in {manager}'s install.")

        process.stdin.write(products_json_bytes)
        process.stdin.close()
        await process.stdin.wait_closed()

        with open(pipe_from_sub_path, "r", encoding="ascii") as pipe_from_sub:
            with open(pipe_to_sub_path, "w", encoding="ascii") as pipe_to_sub:
                while True:
                    header = pipe_read_line(pipe_from_sub)

                    if header == "END":
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            pipe_to_sub,
                            pipe_from_sub,
                            daemon_reader,
                            daemon_writer,
                            daemon_workdir_path,
                            destination_relative_path,
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


async def install_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    if manager == "PP":
        installer = partial(
            PPpackage_sub.install,
            destination_path=daemon_workdir_path / destination_relative_path,
        )
    else:
        installer = partial(
            install_external_manager,
            manager=manager,
            managers_path=managers_path,
            daemon_reader=daemon_reader,
            daemon_writer=daemon_writer,
            daemon_workdir_path=daemon_workdir_path,
            destination_relative_path=destination_relative_path,
        )

    await installer(
        debug=debug,
        cache_path=cache_path,
        versions=versions,
        product_ids=product_ids,
    )


async def resolve_external_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    requirements: Iterable[Any],
    options: Mapping[str, Any] | None,
) -> Iterable[Any]:
    manager_command_path = get_manager_command_path(managers_path, manager)

    process = await create_subprocess_exec(
        str(manager_command_path),
        "--debug" if debug else "--no-debug",
        "resolve",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    indent = 4 if debug else None

    resolve_input_json = json.dumps(
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

    lockfiles = json.loads(lockfiles_json)

    return lockfiles


async def resolve_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    requirements: Iterable[Any],
    options: Mapping[str, Any] | None,
    manager_lockfiles: MutableMapping[str, Iterable[Any]],
) -> None:
    if manager == "PP":
        resolver = PPpackage_sub.resolve
    else:
        resolver = partial(
            resolve_external_manager, manager=manager, managers_path=managers_path
        )

    lockfiles = await resolver(
        debug=debug, cache_path=cache_path, requirements=requirements, options=options
    )

    manager_lockfiles[manager] = lockfiles


async def fetch_external_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    manager_command_path = get_manager_command_path(managers_path, manager)

    process = create_subprocess_exec(
        str(manager_command_path),
        "--debug" if debug else "--no-debug",
        "fetch",
        str(cache_path),
        str(generators_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

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
        print(f"DEBUG PPpackage: sending to {manager}'s fetch:", file=stderr)
        print(fetch_input_json, file=stderr)

    fetch_input_json_bytes = fetch_input_json.encode("ascii")

    product_ids_json_bytes = await asubprocess_communicate(
        await process,
        f"Error in {manager}'s fetch.",
        fetch_input_json_bytes,
    )

    product_ids_json = product_ids_json_bytes.decode("ascii")

    if debug:
        print(f"DEBUG PPpackage: received from {manager}'s fetch:", file=stderr)
        print(product_ids_json, file=stderr)

    product_ids = json.loads(product_ids_json)

    return product_ids


async def fetch_manager(
    debug: bool,
    manager: str,
    managers_path: Path,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
    manager_product_ids_dict: MutableMapping[str, Mapping[str, str]],
) -> None:
    if manager == "PP":
        fetcher = PPpackage_sub.fetch
    else:
        fetcher = partial(
            fetch_external_manager, manager=manager, managers_path=managers_path
        )

    product_ids = await fetcher(
        debug=debug,
        cache_path=cache_path,
        versions=versions,
        options=options,
        generators=generators,
        generators_path=generators_path,
    )

    manager_product_ids_dict[manager] = product_ids


async def resolve(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    manager_requirements: Mapping[str, Iterable[Any]],
    manager_options_dict: Mapping[str, Any],
) -> Mapping[str, Mapping[str, str]]:
    manager_lockfiles: MutableMapping[str, Iterable[Mapping[str, str]]] = {}

    async with TaskGroup() as group:
        for manager, requirements in manager_requirements.items():
            options = manager_options_dict.get(manager)

            group.create_task(
                resolve_manager(
                    debug,
                    manager,
                    managers_path,
                    cache_path,
                    requirements,
                    options,
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

    async with TaskGroup() as group:
        for manager, versions in manager_versions_dict.items():
            options = manager_options_dict.get(manager)

            group.create_task(
                fetch_manager(
                    debug,
                    manager,
                    managers_path,
                    cache_path,
                    versions,
                    options,
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


def generate_machine_id(machine_id_path: Path):
    if machine_id_path.exists():
        return

    machine_id_path.parent.mkdir(exist_ok=True, parents=True)

    with machine_id_path.open("w") as machine_id_file:
        machine_id_file.write(
            "".join(random.choices([str(digit) for digit in range(10)], k=32)) + "\n"
        )


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id


@asynccontextmanager
async def communicate_with_daemon(
    daemon_path: Path,
):
    (
        daemon_reader,
        daemon_writer,
    ) = await open_unix_connection(daemon_path)

    try:
        yield daemon_reader, daemon_writer
    finally:
        stream_write_line(daemon_writer, "END")
        await daemon_writer.drain()
        daemon_writer.close()
        await daemon_writer.wait_closed()


machine_id_relative_path = Path("etc") / "machine-id"


async def install(
    debug: bool,
    managers_path: Path,
    cache_path: Path,
    daemon_socket_path: Path,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    manager_versions_dict: Mapping[str, Mapping[str, str]],
    manager_product_ids_dict: Mapping[str, Mapping[str, str]],
) -> None:
    generate_machine_id(
        daemon_workdir_path / destination_relative_path / machine_id_relative_path
    )

    machine_id = read_machine_id(Path("/") / machine_id_relative_path)

    async with communicate_with_daemon(daemon_socket_path) as (
        daemon_reader,
        daemon_writer,
    ):
        stream_write_string(daemon_writer, machine_id)

        for manager, versions in manager_versions_dict.items():
            product_ids = manager_product_ids_dict[manager]

            await install_manager(
                debug,
                manager,
                managers_path,
                cache_path,
                daemon_reader,
                daemon_writer,
                daemon_workdir_path,
                destination_relative_path,
                versions,
                product_ids,
            )


app = AsyncTyper()


@app.command()
async def main(
    managers_path: Path,
    cache_path: Path,
    generators_path: Path,
    daemon_socket_path: Path,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    debug: bool = False,
) -> None:
    print("*MESSAGE*", file=stderr)

    requirements_generators_input = json.load(stdin)

    requirements, options, generators = parse_input(requirements_generators_input)

    versions = await resolve(debug, managers_path, cache_path, requirements, options)

    product_ids = await fetch(
        debug, managers_path, cache_path, versions, options, generators, generators_path
    )

    await install(
        debug,
        managers_path,
        cache_path,
        daemon_socket_path,
        daemon_workdir_path,
        destination_relative_path,
        versions,
        product_ids,
    )


if __name__ == "__main__":
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"PPpackage: {e}", file=stderr)
        exit(1)
