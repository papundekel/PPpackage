from asyncio import Queue as SimpleQueue
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
from PPpackage_utils.submanager import discard_build_results_context
from PPpackage_utils.utils import Queue, ensure_dir_exists, fakeroot, queue_put_loop

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
    success: SimpleQueue[bool],
    results: Queue[PackageIDAndInfo],
) -> None:
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

            return_code = await process.wait()

            if return_code != 0:
                results.put_nowait(None)
                success.put_nowait(False)
                return

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

        async with queue_put_loop(results):
            for package_name in package_names:
                line = (await process.stdout.readline()).decode()

                if line == "":
                    success.put_nowait(False)
                    return

                line = line.strip()

                await results.put(
                    PackageIDAndInfo(
                        name=package_name,
                        id_and_info=IDAndInfo(
                            product_id=process_product_id(line), product_info=None
                        ),
                    )
                )

        return_code = await process.wait()

        if return_code != 0:
            success.put_nowait(False)
            return

        success.put_nowait(True)
