from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage_utils.parse import FetchInput, FetchOutput, FetchOutputValue
from PPpackage_utils.utils import asubprocess_communicate, ensure_dir_exists, fakeroot

from .utils import get_cache_paths


async def fetch(
    cache_path: Path,
    input: FetchInput,
) -> FetchOutput:
    database_path, cache_path = get_cache_paths(cache_path)

    ensure_dir_exists(cache_path)

    packages = list(input.packages.keys())

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

    output: MutableMapping[str, FetchOutputValue] = {}

    for package, line in zip(packages, stdout.decode("ascii").splitlines()):
        package_version_split = (
            line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
        )

        product_id = f"{package_version_split[-2]}-{package_version_split[-1]}"

        output[package] = FetchOutputValue(product_id=product_id, product_info=None)

    return FetchOutput(output)
