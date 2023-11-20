from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import Iterable, Set
from pathlib import Path
from sys import stderr

from PPpackage_utils.parse import Product
from PPpackage_utils.utils import (
    asubprocess_communicate,
    communicate_from_sub,
    ensure_dir_exists,
    fakeroot,
)

from .utils import get_cache_paths


async def install(
    cache_path: Path,
    destination_path: Path,
    pipe_from_sub_path: Path,
    pipe_to_sub_path: Path,
    products: Iterable[Product],
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
                        / f"{product.name}-{product.version}-{product.product_id}.pkg.tar.zst"
                    )
                    for product in products
                ],
                stdin=DEVNULL,
                stdout=stderr,
                stderr=None,
                env=environment,
            )

            await asubprocess_communicate(process, "Error in `pacman -Udd`")
