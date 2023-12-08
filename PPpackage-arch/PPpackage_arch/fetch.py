from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import (
    BuildResult,
    Dependency,
    IDAndInfo,
    Options,
    Package,
    PackageIDAndInfo,
)
from PPpackage_utils.submanager import (
    SubmanagerCommandFailure,
    discard_build_results_context,
)
from PPpackage_utils.utils import asubprocess_wait, ensure_dir_exists, fakeroot

from .utils import get_cache_paths


def process_product_id(line: str):
    package_version_split = (
        line.rsplit("/", 1)[-1].partition(".pkg.tar.zst")[0].rsplit("-", 2)
    )

    return f"{package_version_split[-2]}-{package_version_split[-1]}"


async def fetch(
    debug: bool,
    data: None,
    session_data: Any,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> AsyncIterable[PackageIDAndInfo]:
    async with discard_build_results_context(build_results):
        database_path, cache_path = get_cache_paths(cache_path)

        ensure_dir_exists(cache_path)

        package_names = []

        async for package, dependencies in packages:
            package_names.append(package.name)

            async for _ in dependencies:
                pass

        async with fakeroot(debug) as environment:
            process = await create_subprocess_exec(
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
                stdout=DEVNULL,
                stderr=DEVNULL,
                env=environment,
            )

            await asubprocess_wait(process, SubmanagerCommandFailure())

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
            *package_names,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=DEVNULL,
        )

        assert process.stdout is not None
        for package_name in package_names:
            line = (await process.stdout.readline()).decode()

            if line == "":
                raise SubmanagerCommandFailure

            line = line.strip()

            yield PackageIDAndInfo(
                name=package_name,
                id_and_info=IDAndInfo(
                    product_id=process_product_id(line), product_info=None
                ),
            )

        await asubprocess_wait(process, SubmanagerCommandFailure())
