from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Iterable
from pathlib import Path
from sys import stderr

from PPpackage_utils.parse import FetchOutputValue, Options, PackageWithDependencies
from PPpackage_utils.utils import asubprocess_communicate, ensure_dir_exists, fakeroot

from .utils import get_cache_paths


def process_product_id(line: str):
    package_version_split = (
        line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
    )

    return f"{package_version_split[-2]}-{package_version_split[-1]}"


async def fetch(
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[PackageWithDependencies],
) -> Iterable[FetchOutputValue]:
    database_path, cache_path = get_cache_paths(cache_path)

    ensure_dir_exists(cache_path)

    package_names = [package.name async for package in packages]

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
            "--nodeps",
            "--nodeps",
            *package_names,
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
        *package_names,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacman -Sddp`")

    return [
        FetchOutputValue(
            name=package_name,
            product_id=process_product_id(line),
            product_info=None,
        )
        for package_name, line in zip(
            package_names, stdout.decode("ascii").splitlines()
        )
    ]
