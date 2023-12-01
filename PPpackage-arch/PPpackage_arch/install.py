from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
    TemporaryDirectory,
    asubprocess_wait,
    communicate_from_sub,
    ensure_dir_exists,
    fakeroot,
)

from .utils import get_cache_paths


async def install(
    debug: bool,
    cache_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
    runner_workdir_path: Path,
    old_directory: memoryview,
    products: AsyncIterable[Product],
) -> memoryview:
    _, cache_path = get_cache_paths(cache_path)
    database_path_relative = Path("var") / "lib" / "pacman"

    with TemporaryDirectory(runner_workdir_path) as destination_path:
        with TarFileInMemoryRead(old_directory) as old_tar:
            old_tar.extractall(destination_path)

        database_path = destination_path / database_path_relative

        ensure_dir_exists(database_path)

        with communicate_from_sub(pipe_from_sub_path):
            async with fakeroot(debug) as environment:
                environment["LD_LIBRARY_PATH"] += ":/usr/share/libalpm-pp/usr/lib/"
                environment[
                    "LD_PRELOAD"
                ] += f":fakealpm/build/install/lib/libfakealpm.so"
                environment["PP_PIPE_FROM_SUB_PATH"] = str(pipe_from_sub_path)
                environment["PP_PIPE_TO_SUB_PATH"] = str(pipe_to_sub_path)
                environment["PP_RUNNER_WORKDIR_RELATIVE_PATH"] = str(
                    destination_path.relative_to(runner_workdir_path)
                )

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
                            / f"{product.name}-{product.version}-{product.product_id}.pkg.tar.zst"
                        )
                        async for product in products
                    ],
                    stdin=DEVNULL,
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                    env=environment,
                )

                await asubprocess_wait(process, "Error in `pacman -Udd`")

        with TarFileInMemoryWrite() as new_tar:
            new_tar.add(str(destination_path), "")

        return new_tar.data
