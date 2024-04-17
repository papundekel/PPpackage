from asyncio import Lock, create_subprocess_exec
from contextlib import contextmanager
from pathlib import Path
from sys import stderr

from asyncstdlib import list as async_list

from PPpackage.container_utils.run import run as container_run
from PPpackage.container_utils.translate import translate
from PPpackage.installer.interface.exceptions import InstallerException
from PPpackage.utils.asyncio_stream import start_unix_server
from PPpackage.utils.stream import Reader, Writer, dump_one
from PPpackage.utils.utils import (
    TemporaryDirectory,
    TemporaryPipe,
    asubprocess_wait,
    ensure_dir_exists,
)

from .schemes import ContainerizerConfig, Parameters


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
    containerizer_config: ContainerizerConfig,
    installation_path: Path,
    reader: Reader,
    writer: Writer,
):
    command = await reader.load_one(str)
    args = reader.load_many(str)

    with TemporaryPipe() as pipe_hook_path:
        args = await async_list(args)

        await writer.write(dump_one(str(pipe_hook_path)))

        with (
            pipe_hook_path.open("rb") as pipe_hook,
            create_necessary_container_files(installation_path),
        ):
            return_code = container_run(
                containerizer_config.url,
                [command, *args],
                stdin=pipe_hook.read(),
                rootfs=str(
                    translate(containerizer_config.path_translations, installation_path)
                ),
            )

    await writer.write(dump_one(return_code))


DATABASE_PATH_RELATIVE = Path("var") / Path("lib") / Path("pacman")


lock = Lock()


async def install(parameters: Parameters, product_path: Path, installation_path: Path):
    database_path = installation_path / DATABASE_PATH_RELATIVE

    ensure_dir_exists(database_path)

    with TemporaryDirectory() as server_socket_directory_path:
        server_socket_path = server_socket_directory_path / "server.sock"

        server = await start_unix_server(
            lambda reader, writer: install_manager_command(
                parameters.containerizer, installation_path, reader, writer
            ),
            server_socket_path,
        )

        await server.start_serving()

        async with lock:
            process = await create_subprocess_exec(
                "/usr/local/bin/fakealpm",
                "/usr/local/bin/fakealpm-executable",
                str(server_socket_path),
                str(installation_path),
                str(database_path),
                str(product_path),
            )

            await asubprocess_wait(process, InstallerException)

        server.close()
