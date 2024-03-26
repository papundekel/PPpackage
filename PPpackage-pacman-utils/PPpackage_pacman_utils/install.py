from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import MutableMapping
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.utils import containerizer_subprocess_exec
from PPpackage_utils.pipe import (
    pipe_read_line_maybe,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
)
from PPpackage_utils.utils import (
    ContainerizerWorkdirInfo,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
    fakeroot,
)


@contextmanager
def create_necessary_container_files(root_path: Path):
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
    containerizer: str,
    workdir_info: ContainerizerWorkdirInfo,
    pipe_to_fakealpm: TextIOWrapper,
    pipe_from_fakealpm: TextIOWrapper,
    installation_path: Path,
):
    command = pipe_read_string("PPpackage-pacman-utils", pipe_from_fakealpm)
    args = pipe_read_strings("PPpackage-pacman-utils", pipe_from_fakealpm)

    with TemporaryPipe() as pipe_hook_path:
        args = [*args][1:]

        pipe_write_string(
            "PPpackage-pacman-utils", pipe_to_fakealpm, str(pipe_hook_path)
        )
        pipe_to_fakealpm.flush()

        with (
            pipe_hook_path.open("r") as pipe_hook,
            create_necessary_container_files(installation_path),
        ):
            async with containerizer_subprocess_exec(
                containerizer,
                "run",
                "--rm",
                "--interactive",
                "--rootfs",
                str(workdir_info.translate(installation_path)),
                command,
                *args,
                stdin=pipe_hook,
                stdout=DEVNULL,
                stderr=DEVNULL,
            ) as process:
                return_code = await process.wait()

    pipe_write_int("PPpackage-pacman-utils", pipe_to_fakealpm, return_code)
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


async def pacman_install(
    containerizer: str,
    workdir_info: ContainerizerWorkdirInfo,
    installation_path: Path,
    product_path: Path,
):
    database_path = installation_path / DATABASE_PATH_RELATIVE

    ensure_dir_exists(database_path)

    with (
        TemporaryPipe() as pipe_from_fakealpm_path,
        TemporaryPipe() as pipe_to_fakealpm_path,
    ):
        async with fakeroot() as environment:
            create_environment(
                environment, pipe_from_fakealpm_path, pipe_to_fakealpm_path
            )

            process = await create_subprocess_exec(
                "pacman",
                "--noconfirm",
                "--needed",
                "--dbpath",
                str(database_path),
                "--root",
                str(installation_path),
                "--upgrade",
                "--nodeps",
                "--nodeps",
                str(product_path),
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=None,
                env=environment,
            )

            with (
                open(pipe_from_fakealpm_path, "r") as pipe_from_fakealpm,
                open(pipe_to_fakealpm_path, "w") as pipe_to_fakealpm,
            ):
                while True:
                    header = pipe_read_line_maybe(
                        "PPpackage-pacman-utils", pipe_from_fakealpm
                    )

                    if header is None:
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            containerizer,
                            workdir_info,
                            pipe_to_fakealpm,
                            pipe_from_fakealpm,
                            installation_path,
                        )
                    else:
                        raise Exception(
                            f"Unknown header: {header}", "PPpackage-pacman-utils"
                        )

            await asubprocess_wait(process, CommandException())
