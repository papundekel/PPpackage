from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable
from os import symlink
from pathlib import Path

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Dependency, Options, Package, PackageIDAndInfo
from PPpackage_utils.utils import (
    TemporaryDirectory,
    asubprocess_wait,
    discard_async_iterable,
    ensure_dir_exists,
    fakeroot,
)

from .utils import get_cache_paths


def process_product_id(line: str):
    package_version_split = (
        line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
    )

    return f"{package_version_split[-2]}-{package_version_split[-1]}"


async def fetch(
    debug: bool,
    data: None,
    cache_path: Path,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation: memoryview | None,
    generators: memoryview | None,
) -> PackageIDAndInfo | AsyncIterable[str]:
    database_path, cache_path = get_cache_paths(cache_path)

    ensure_dir_exists(cache_path)

    await discard_async_iterable(dependencies)

    with TemporaryDirectory() as database_path_fake:
        symlink(database_path / "sync", database_path_fake / "sync")

        async with fakeroot(debug) as environment:
            process = await create_subprocess_exec(
                "pacman",
                "--dbpath",
                str(database_path_fake),
                "--cachedir",
                str(cache_path),
                "--noconfirm",
                "--sync",
                "--downloadonly",
                "--nodeps",
                "--nodeps",
                package.name,
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=None,
                env=environment,
            )

            await asubprocess_wait(process, CommandException())

    process = await create_subprocess_exec(
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
        package.name,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    assert process.stdout is not None

    line = (await process.stdout.readline()).decode().strip()

    if line == "":
        raise CommandException

    id_and_info = PackageIDAndInfo(
        product_id=process_product_id(line),
        product_info=None,
    )

    await asubprocess_wait(process, CommandException())

    return id_and_info
