#!/usr/bin/env python

from PPpackage_utils import (
    MyException,
    AsyncTyper,
    asubprocess_communicate,
    check_dict_format,
    parse_generators,
    SetEncoder,
)

import subprocess
import itertools
import json
import sys
import os
import asyncio


def check_requirements(manager_requirements_input):
    if type(manager_requirements_input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in manager_requirements_input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")


def parse_requirements(input):
    check_requirements(input)

    requirements = input

    return requirements


def merge_lockfiles(versions, product_ids):
    return {
        package: {"version": versions[package], "product_id": product_ids[package]}
        for package in versions
        if package in product_ids
    }


def get_manager_path(managers_path, manager):
    return os.path.join(managers_path, f"PPpackage_{manager}.py")


def check_options(input):
    if type(input) is not dict:
        raise MyException("Invalid options format.")

    for options_input in input.values():
        if type(options_input) is not dict:
            raise MyException("Invalid options format.")


def parse_options(input):
    check_options(input)

    options = input

    return options


def parse_input(input):
    check_dict_format(
        input,
        {"requirements", "options", "generators"},
        set(),
        "Invalid input format.",
    )

    requirements = parse_requirements(input["requirements"])
    options = parse_options(input["options"])
    generators = parse_generators(input["generators"])

    return requirements, options, generators


def generator_versions(generators_path, manager_versions_dict, manager_product_ids):
    versions_path = os.path.join(generators_path, "versions")

    for manager, versions in manager_versions_dict.items():
        manager_path = os.path.join(versions_path, manager)

        os.makedirs(manager_path, exist_ok=True)

        product_ids = manager_product_ids[manager]

        for package, version in versions.items():
            product_id = product_ids[package]

            with open(
                os.path.join(manager_path, f"{package}.json"), "w"
            ) as versions_file:
                json.dump(
                    {"version": version, "product_id": product_id},
                    versions_file,
                    indent=4,
                )


builtin_generators = {"versions": generator_versions}


async def install_manager(
    debug,
    managers_path,
    cache_path,
    manager_product_ids_dict,
    destination_path,
    manager,
    versions,
):
    manager_path = get_manager_path(managers_path, manager)

    process = asyncio.create_subprocess_exec(
        manager_path,
        "--debug" if debug else "--no-debug",
        "install",
        cache_path,
        destination_path,
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

    await asubprocess_communicate(
        await process,
        f"Error in {manager}'s install.",
        products_json_bytes,
    )


async def resolve_manager(
    debug,
    managers_path,
    cache_path,
    manager,
    requirements,
    manager_options_dict,
    manager_lockfiles,
):
    manager_path = get_manager_path(managers_path, manager)

    process = asyncio.create_subprocess_exec(
        manager_path,
        "--debug" if debug else "--no-debug",
        "resolve",
        cache_path,
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
    debug,
    managers_path,
    cache_path,
    manager,
    versions,
    manager_options_dict,
    generators,
    generators_path,
    manager_product_ids_dict,
):
    manager_path = get_manager_path(managers_path, manager)

    process = asyncio.create_subprocess_exec(
        manager_path,
        "--debug" if debug else "--no-debug",
        "fetch",
        cache_path,
        generators_path,
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
    debug, managers_path, cache_path, manager_requirements, manager_options_dict
):
    manager_lockfiles = {}

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

    lockfiles = [
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
    debug,
    managers_path,
    cache_path,
    manager_versions_dict,
    manager_options_dict,
    generators,
    generators_path,
):
    manager_product_ids_dict = {}

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
    debug,
    managers_path,
    cache_path,
    manager_versions_dict,
    manager_product_ids_dict,
    destination_path,
):
    async with asyncio.TaskGroup() as group:
        for manager, versions in manager_versions_dict.items():
            group.create_task(
                install_manager(
                    debug,
                    managers_path,
                    cache_path,
                    manager_product_ids_dict,
                    destination_path,
                    manager,
                    versions,
                )
            )


app = AsyncTyper()


@app.command()
async def main(
    managers_path: str,
    cache_path: str,
    generators_path: str,
    destination_path: str,
    debug: bool = False,
):
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
