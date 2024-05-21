from asyncio import (
    Lock,
    StreamReader,
    StreamWriter,
    create_subprocess_exec,
    start_unix_server,
)
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from asyncstdlib import list as async_list

from PPpackage.installer.interface.exceptions import InstallerException
from PPpackage.utils.container import Containerizer
from PPpackage.utils.file import TemporaryDirectory, TemporaryPipe
from PPpackage.utils.lock.by_key import lock_by_key
from PPpackage.utils.serialization.asyncio import AsyncioReader, AsyncioWriter
from PPpackage.utils.serialization.writer import dump_one

from .schemes import Parameters


@contextmanager
def create_necessary_container_files(root_path: Path):
    hostname_path = root_path / "etc" / "hostname"
    containerenv_path = root_path / "run" / ".containerenv"

    try:
        hostname_path.parent.mkdir(parents=True, exist_ok=True)
        containerenv_path.parent.mkdir(parents=True, exist_ok=True)

        hostname_path.touch()
        containerenv_path.touch()

        yield

    finally:
        hostname_path.unlink()
        containerenv_path.unlink()


async def install_manager_command(
    containerizer: Containerizer,
    installation_path: Path,
    stream_reader: StreamReader,
    stream_writer: StreamWriter,
):
    reader = AsyncioReader(stream_reader)
    writer = AsyncioWriter(stream_writer)

    command = await reader.load_one(str)
    args = reader.load_many(str)

    with TemporaryPipe() as pipe_hook_path:
        args = await async_list(args)

        await writer.write(dump_one(str(pipe_hook_path)))

        with (
            pipe_hook_path.open("rb") as pipe_hook,
            create_necessary_container_files(installation_path),
        ):
            return_code = containerizer.run(
                [command, *args],
                stdin=pipe_hook.read(),
                rootfs=str(containerizer.translate(installation_path)),
            )

    await writer.write(dump_one(return_code))


DATABASE_PATH_RELATIVE = Path("var") / "lib" / "pacman"


locks = dict[Path, Lock]()


async def install(parameters: Parameters, product_path: Path, installation_path: Path):
    database_path = installation_path / DATABASE_PATH_RELATIVE

    database_path.mkdir(parents=True, exist_ok=True)

    containerizer = Containerizer(parameters.containerizer)

    with TemporaryDirectory() as server_socket_directory_path:
        server_socket_path = server_socket_directory_path / "server.sock"

        server = await start_unix_server(
            partial(install_manager_command, containerizer, installation_path),
            server_socket_path,
        )

        await server.start_serving()

        async with lock_by_key(locks, installation_path):
            process = await create_subprocess_exec(
                "/usr/local/bin/fakealpm",
                "/usr/local/bin/fakealpm-executable",
                str(server_socket_path),
                str(installation_path),
                str(database_path),
                str(product_path),
            )

            return_code = await process.wait()

            if return_code != 0:
                raise InstallerException(
                    f"fakealpm exited with non-zero return code: {return_code}"
                )

        server.close()
