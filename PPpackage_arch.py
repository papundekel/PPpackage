#!/usr/bin/env python

from PPpackage_utils import (
    Product,
    MyException,
    asubprocess_communicate,
    parse_lockfile_simple,
    parse_products_simple,
    init,
    app,
    run,
    ensure_dir_exists,
)

import sys
import subprocess
import re
import os
import asyncio
from pathlib import Path
from collections.abc import Iterable, Mapping, MutableSet, Set, MutableMapping
from typing import Any

regex_package_name = re.compile(r"[a-zA-Z0-9\-@._+]+")


def get_cache_paths(cache_path: Path) -> tuple[Path, Path]:
    database_path = cache_path / "arch" / "db"
    cache_path = cache_path / "arch" / "cache"
    return database_path, cache_path


def check_requirements(input: Any) -> Iterable[str]:
    if type(input) is not list:
        raise MyException("Invalid requirements format")

    for requirement_input in input:
        if type(requirement_input) is not str:
            raise MyException("Invalid requirements format")

    return input


def parse_requirements(input: Any) -> Iterable[str]:
    input_checked = check_requirements(input)

    requirements = input_checked

    return requirements


def parse_options(input: Any) -> Any:
    return None


async def resolve_requirement(
    database_path: Path, requirement: str, dependencies: MutableSet[str]
) -> None:
    process = asyncio.create_subprocess_exec(
        "pactree",
        "--dbpath",
        str(database_path),
        "--sync",
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
        dependencies.add(dependency)


@app.command("update-db")
async def update_database(cache_path: Path) -> None:
    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    process = asyncio.create_subprocess_exec(
        "fakeroot",
        "pacman",
        "--dbpath",
        str(database_path),
        "--sync",
        "--refresh",
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
    )

    await asubprocess_communicate(await process, "Error in `pacman --sync --refresh`")


async def submanagers() -> Iterable[str]:
    return []


async def resolve(
    cache_path: Path, requirements: Iterable[str], options: Any
) -> Iterable[Mapping[str, str]]:
    database_path, _ = get_cache_paths(cache_path)

    # trivial resolution of same-named packages
    requirements = set(requirements)

    dependencies: MutableSet[str] = set()

    async with asyncio.TaskGroup() as group:
        for requirement in requirements:
            group.create_task(
                resolve_requirement(database_path, requirement, dependencies)
            )

    process = asyncio.create_subprocess_exec(
        "pacinfo",
        "--dbpath",
        str(database_path),
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


async def fetch(
    cache_path: Path,
    lockfile: Mapping[str, str],
    options: Any,
    generators: Set[str],
    generators_path: Path,
) -> Mapping[str, str]:
    database_path, cache_path = get_cache_paths(cache_path)

    ensure_dir_exists(cache_path)

    packages = list(lockfile.keys())

    process = asyncio.create_subprocess_exec(
        "fakeroot",
        "pacman",
        "--dbpath",
        str(database_path),
        "--cachedir",
        str(cache_path),
        "--noconfirm",
        "--sync",
        "--downloadonly",
        *packages,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
    )

    await asubprocess_communicate(
        await process, "Error in `pacman --sync --downloadonly`."
    )

    process = asyncio.create_subprocess_exec(
        "pacman",
        "--dbpath",
        str(database_path),
        "--cachedir",
        str(cache_path),
        "--noconfirm",
        "--sync",
        "--nodeps",
        "--nodeps",
        "--print",
        *packages,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(
        await process, "Error in `pacman --sync --print`"
    )

    product_ids: MutableMapping[str, str] = {}

    for package, line in zip(packages, stdout.decode("ascii").splitlines()):
        package_version_split = (
            line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
        )

        product_id = f"{package_version_split[-2]}-{package_version_split[-1]}"

        product_ids[package] = product_id

    return product_ids


async def install(
    cache_path: Path, products: Set[Product], destination_path: Path
) -> None:
    _, cache_path = get_cache_paths(cache_path)
    database_path = destination_path / "var" / "lib" / "pacman"

    ensure_dir_exists(database_path)

    environment = os.environ.copy()
    environment["FAKECHROOT_CMD_SUBST"] = "/usr/bin/ldconfig=/usr/bin/true"

    process = asyncio.create_subprocess_exec(
        "fakechroot",
        "fakeroot",
        "pacman",
        "--noconfirm",
        "--needed",
        "--dbpath",
        str(database_path),
        "--cachedir",
        str(cache_path),
        "--root",
        str(destination_path),
        "--upgrade",
        "--nodeps",
        "--nodeps",
        *[
            str(
                cache_path
                / f"{product.package}-{product.version}-{product.product_id}.pkg.tar.zst"
            )
            for product in products
        ],
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=None,
        env=environment,
    )

    await asubprocess_communicate(await process, "Error in `pacman --upgrade`")


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
