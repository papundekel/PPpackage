#!/usr/bin/env python

from PPpackage_utils import (
    MyException,
    asubprocess_communicate,
    parse_lockfile_simple,
    parse_products_simple,
    init,
    app,
    run,
)

import sys
import subprocess
import re
import os
import asyncio


regex_package_name = re.compile(r"[a-zA-Z0-9\-@._+]+")


def get_cache_paths(cache_path):
    database_path = f"{cache_path}/arch/db"
    cache_path = f"{cache_path}/arch/cache"
    return database_path, cache_path


def check_requirements(input):
    if type(input) is not list:
        raise MyException("Invalid requirements format")

    for requirement_input in input:
        if type(requirement_input) is not str:
            raise MyException("Invalid requirements format")


def parse_requirements(input):
    check_requirements(input)

    requirements = input

    return requirements


def parse_options(input):
    return None


async def resolve_requirement(database_path, requirement, dependencies):
    process = asyncio.create_subprocess_exec(
        "pactree",
        "--dbpath",
        database_path,
        "-s",
        requirement,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pactree`.")

    for line in stdout.decode("utf-8").splitlines():
        match = regex_package_name.search(line)

        if match is None:
            raise MyException("Invalid pactree output.")

        dependency = match.group()
        dependencies.append(dependency)


@app.command("update-db")
async def update_database(cache_path: str):
    database_path, _ = get_cache_paths(cache_path)

    os.makedirs(database_path, exist_ok=True)

    process = asyncio.create_subprocess_exec(
        "fakeroot",
        "pacman",
        "--dbpath",
        database_path,
        "-Sy",
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
    )

    await asubprocess_communicate(await process, "Error in `pacman -Sy`")


async def submanagers():
    return []


async def resolve(cache_path, requirements, options):
    database_path, _ = get_cache_paths(cache_path)

    # trivial resolution of same-named packages
    requirements = set(requirements)

    dependencies = []

    async with asyncio.TaskGroup() as group:
        for requirement in requirements:
            group.create_task(
                resolve_requirement(database_path, requirement, dependencies)
            )

    # trivial resolution of same-named packages
    dependencies = list(set(dependencies))

    process = asyncio.create_subprocess_exec(
        "pacinfo",
        "--dbpath",
        database_path,
        "--short",
        *dependencies,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacinfo`.")

    lockfile = {}

    for line in stdout.decode("ascii").splitlines():
        if line.startswith(" "):
            continue

        split_line = line.split()

        package = split_line[0].split("/")[-1]
        version = split_line[1].rsplit("-", 1)[0]

        lockfile[package] = version

    return [lockfile]


async def fetch(cache_path, lockfile, options, generators, generators_path):
    database_path, cache_path = get_cache_paths(cache_path)

    os.makedirs(cache_path, exist_ok=True)

    packages = list(lockfile.keys())

    process = asyncio.create_subprocess_exec(
        "fakeroot",
        "pacman",
        "--dbpath",
        database_path,
        "--cachedir",
        cache_path,
        "--noconfirm",
        "-Sw",
        *packages,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
    )

    await asubprocess_communicate(await process, "Error in `pacman -Sw`.")

    process = asyncio.create_subprocess_exec(
        "pacman",
        "--dbpath",
        database_path,
        "--cachedir",
        cache_path,
        "--noconfirm",
        "-Sddp",
        *packages,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacman -Sddp`")

    product_ids = {}

    for package, line in zip(packages, stdout.decode("ascii").splitlines()):
        package_version_split = (
            line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
        )

        product_id = f"{package_version_split[-2]}-{package_version_split[-1]}"

        product_ids[package] = product_id

    return product_ids


async def install(cache_path, products, destination_path):
    _, cache_path = get_cache_paths(cache_path)
    database_path = f"{destination_path}/var/lib/pacman"

    os.makedirs(database_path, exist_ok=True)

    environment = os.environ.copy()
    environment["FAKECHROOT_CMD_SUBST"] = "/usr/bin/ldconfig=/usr/bin/true"

    process = asyncio.create_subprocess_exec(
        "fakechroot",
        "fakeroot",
        "pacman",
        "--noconfirm",
        "--needed",
        "--dbpath",
        database_path,
        "--cachedir",
        cache_path,
        "--root",
        destination_path,
        "-Udd",
        *[
            f"{cache_path}/{product.package}-{product.version}-{product.product_id}.pkg.tar.zst"
            for product in products
        ],
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
        env=environment,
    )

    await asubprocess_communicate(await process, "Error in `pacman -Udd`")


if __name__ == "__main__":
    init(
        submanagers,
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_options,
        parse_lockfile_simple,
        parse_products_simple,
    )
    run("arch")
