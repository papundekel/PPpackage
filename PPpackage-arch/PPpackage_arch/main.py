from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable, Mapping, MutableMapping, MutableSet, Set
from pathlib import Path
from re import compile as re_compile
from sys import stderr
from typing import Any

from PPpackage_utils.app import init, run
from PPpackage_utils.io import pipe_read_int, pipe_read_string, pipe_write_string
from PPpackage_utils.utils import (
    MyException,
    Product,
    asubprocess_communicate,
    communicate_from_sub,
    ensure_dir_exists,
    fakeroot,
    parse_lockfile_simple,
    parse_products_simple,
)

regex_package_name = re_compile(r"[a-zA-Z0-9\-@._+]+")


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
    process = create_subprocess_exec(
        "pactree",
        "--dbpath",
        str(database_path),
        "--sync",
        requirement,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pactree`.")

    for line in stdout.decode("utf-8").splitlines():
        match = regex_package_name.search(line)

        if match is None:
            raise MyException("Invalid pactree output.")

        dependency = match.group()
        dependencies.add(dependency)


async def update_database(cache_path: Path) -> None:
    database_path, _ = get_cache_paths(cache_path)

    ensure_dir_exists(database_path)

    async with fakeroot() as environment:
        process = create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--sync",
            "--refresh",
            stdin=DEVNULL,
            stdout=stderr,
            stderr=None,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `pacman -Sy`")


async def submanagers() -> Iterable[str]:
    return []


async def resolve(
    cache_path: Path, requirements: Iterable[str], options: Any
) -> Iterable[Mapping[str, str]]:
    database_path, _ = get_cache_paths(cache_path)

    # trivial resolution of same-named packages
    requirements = set(requirements)

    dependencies: MutableSet[str] = set()

    async with TaskGroup() as group:
        for requirement in requirements:
            group.create_task(
                resolve_requirement(database_path, requirement, dependencies)
            )

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

    async with fakeroot() as environment:
        process = create_subprocess_exec(
            "pacman",
            "--dbpath",
            str(database_path),
            "--cachedir",
            str(cache_path),
            "--noconfirm",
            "--sync",
            "--downloadonly",
            *packages,
            stdin=DEVNULL,
            stdout=stderr,
            stderr=None,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `pacman -Sw`.")

    process = create_subprocess_exec(
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
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacman -Sddp`")

    product_ids: MutableMapping[str, str] = {}

    for package, line in zip(packages, stdout.decode("ascii").splitlines()):
        package_version_split = (
            line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
        )

        product_id = f"{package_version_split[-2]}-{package_version_split[-1]}"

        product_ids[package] = product_id

    return product_ids


def hook_command(pipe_from_sub, command, *args):
    pipe_from_sub.write("COMMAND\n")
    pipe_write_string(pipe_from_sub, command)
    for arg in args:
        pipe_write_string(pipe_from_sub, arg)
    pipe_from_sub.write("-1\n")
    pipe_from_sub.flush()

    pipe_hook_path = pipe_read_string(pipe_from_sub)

    with open(pipe_hook_path, "w"):
        pass

    return_value = pipe_read_int(pipe_from_sub)

    return return_value


async def install(
    cache_path: Path,
    products: Set[Product],
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
) -> None:
    _, cache_path = get_cache_paths(cache_path)
    database_path = destination_path / "var" / "lib" / "pacman"

    ensure_dir_exists(database_path)

    with communicate_from_sub(pipe_from_sub_path):
        async with fakeroot() as environment:
            environment["LD_LIBRARY_PATH"] += ":/usr/share/libalpm-pp/usr/lib/"
            environment["LD_PRELOAD"] += ":fakealpm/build/fakealpm.so"
            environment["PP_PIPE_FROM_SUB_PATH"] = str(pipe_from_sub_path)
            environment["PP_PIPE_TO_SUB_PATH"] = str(pipe_to_sub_path)

            process = await create_subprocess_exec(
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
                stdin=DEVNULL,
                stdout=stderr,
                stderr=None,
                env=environment,
            )

            await asubprocess_communicate(process, "Error in `pacman -Udd`")


def main():
    app = init(
        update_database,
        submanagers,
        resolve,
        fetch,
        install,
        parse_requirements,
        parse_options,
        parse_lockfile_simple,
        parse_products_simple,
    )
    run(app, "arch")
