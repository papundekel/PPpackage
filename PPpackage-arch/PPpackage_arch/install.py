from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import MutableMapping
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path
from sys import stderr
from tempfile import NamedTemporaryFile

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Product
from PPpackage_utils.pipe import (
    pipe_read_line_maybe,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.utils import (
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
)

from .settings import Settings
from .utils import get_cache_paths


@contextmanager
def necessary_container_files(root_path: Path):
    hostname_path = root_path / "etc" / "hostname"
    containerenv_path = root_path / "run" / ".containerenv"

    try:
        ensure_dir_exists(hostname_path.parent)
        ensure_dir_exists(containerenv_path.parent)

        hostname_path.touch()
        containerenv_path.touch()

        yield

    finally:
        hostname_path.unlink()
        containerenv_path.unlink()


async def install_manager_command(
    settings: Settings,
    pipe_to_fakealpm: TextIOWrapper,
    pipe_from_fakealpm: TextIOWrapper,
    installation_path: Path,
    containerizer_installation_path: Path,
):
    command = pipe_read_string(settings.debug, "PPpackage-arch", pipe_from_fakealpm)
    args = pipe_read_strings(settings.debug, "PPpackage-arch", pipe_from_fakealpm)

    with TemporaryPipe() as pipe_hook_path:
        args = [*args][1:]

        pipe_write_string(
            settings.debug, "PPpackage-arch", pipe_to_fakealpm, str(pipe_hook_path)
        )
        pipe_to_fakealpm.flush()

        with (
            pipe_hook_path.open("r") as pipe_hook,
            necessary_container_files(installation_path),
            NamedTemporaryFile() as containers_conf,
        ):
            process = await create_subprocess_exec(
                "podman-remote",
                "--url",
                settings.containerizer,
                "run",
                "--rm",
                "--interactive",
                "--rootfs",
                str(containerizer_installation_path),
                command,
                *args,
                stdin=pipe_hook,
                stdout=DEVNULL,
                stderr=stderr,
                env={
                    "CONTAINERS_CONF": containers_conf.name
                },  # hack, allows $HOME to not exist
            )

            return_code = await asubprocess_wait(process, CommandException())

    pipe_write_int(settings.debug, "PPpackage-arch", pipe_to_fakealpm, return_code)
    pipe_to_fakealpm.flush()


def create_environment(
    environment: MutableMapping[str, str],
    pipe_from_fakealpm_path: Path,
    pipe_to_fakealpm_path: Path,
):
    environment["LD_LIBRARY_PATH"] += ":/usr/share/libalpm-pp/usr/lib/"
    environment["LD_PRELOAD"] += f":/usr/local/lib/libfakealpm.so"
    environment["PP_PIPE_FROM_FAKEALPM_PATH"] = str(pipe_from_fakealpm_path)
    environment["PP_PIPE_TO_FAKEALPM_PATH"] = str(pipe_to_fakealpm_path)


DATABASE_PATH_RELATIVE = Path("var") / Path("lib") / Path("pacman")


async def install(
    settings: Settings,
    state: None,
    installation_path: Path,
    product: Product,
):
    containerizer_installation_path = (
        settings.workdir_containerizer
        / installation_path.relative_to(settings.workdir_container)
    )

    _, cache_path = get_cache_paths(settings.cache_path)

    database_path = installation_path / DATABASE_PATH_RELATIVE

    ensure_dir_exists(database_path)

    with (
        TemporaryPipe() as pipe_from_fakealpm_path,
        TemporaryPipe() as pipe_to_fakealpm_path,
    ):
        async with fakeroot(settings.debug) as environment:
            create_environment(
                environment, pipe_from_fakealpm_path, pipe_to_fakealpm_path
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
                str(installation_path),
                "--upgrade",
                "--nodeps",
                "--nodeps",
                str(
                    cache_path
                    / f"{product.name}-{product.version}-{product.product_id}.pkg.tar.zst"
                ),
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
                env=environment,
            )

            with (
                open(pipe_from_fakealpm_path, "r") as pipe_from_fakealpm,
                open(pipe_to_fakealpm_path, "w") as pipe_to_fakealpm,
            ):
                while True:
                    header = pipe_read_line_maybe(
                        settings.debug, "PPpackage-arch", pipe_from_fakealpm
                    )

                    if header is None:
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            settings,
                            pipe_to_fakealpm,
                            pipe_from_fakealpm,
                            installation_path,
                            containerizer_installation_path,
                        )
                    else:
                        raise Exception(f"Unknown header: {header}", "PPpackage-arch")

        await asubprocess_wait(process, CommandException())
