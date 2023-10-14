from asyncio import (
    CancelledError,
    StreamReader,
    StreamWriter,
    create_subprocess_exec,
    get_running_loop,
    start_unix_server,
)
from asyncio.subprocess import PIPE
from contextlib import contextmanager
from io import StringIO
from json import load as json_load
from os import getgid, getuid
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL
from sys import stderr

from pid import PidFile, PidFileAlreadyLockedError
from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.io import (
    stream_read_line,
    stream_read_relative_path,
    stream_read_relative_paths,
    stream_read_string,
    stream_read_strings,
    stream_write_int,
    stream_write_line,
    stream_write_string,
)
from PPpackage_utils.utils import TemporaryDirectory, asubprocess_communicate, json_dump
from typer import Exit


@contextmanager
def edit_json_file(debug: bool, path: Path):
    with path.open("r+") as file:
        data = json_load(file)

        try:
            yield data
        finally:
            file.seek(0)
            file.truncate()

            json_dump(data, file, indent=4 if debug else None)


config_relative_path = Path("config.json")


def edit_config(debug: bool, bundle_path: Path):
    return edit_json_file(debug, bundle_path / config_relative_path)


async def handle_command(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    container_path: Path,
    bundle_path: Path,
    root_path: Path,
) -> bool:
    if not container_path.exists():
        return False

    image_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runner", reader
    )

    command = await stream_read_string(debug, "PPpackage-runner", reader)
    args = [arg async for arg in stream_read_strings(debug, "PPpackage-runner", reader)]

    with edit_config(debug, bundle_path) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

    pipe_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runner", reader
    )

    with pipe_path.open("r") as pipe:
        process = await create_subprocess_exec(
            "runc",
            "--root",
            root_path,
            "run",
            "--bundle",
            str(bundle_path),
            "PPpackage-container",
            stdin=pipe,
            stdout=DEVNULL,
            stderr=None,
        )

        return_code = await process.wait()

    stream_write_int(debug, "PPpackage-runner", writer, return_code)

    return True


async def handle_init(
    debug,
    reader: StreamReader,
    writer: StreamWriter,
    containers_path: Path,
    container_path: Path,
):
    container_path.mkdir(exist_ok=True)

    stream_write_string(
        debug,
        "PPpackage-runner",
        writer,
        str(container_path.relative_to(containers_path)),
    )


async def handle_run(
    debug: bool, reader: StreamReader, writer: StreamWriter, container_path: Path
):
    image_type = await stream_read_line(debug, "PPpackage-runner", reader)

    if image_type == "IMAGE":
        image = await stream_read_string(debug, "PPpackage-runner", reader)
    elif image_type == "DOCKERFILE":
        dockerfile = await stream_read_string(debug, "PPpackage-runner", reader)

        process = await create_subprocess_exec(
            "podman",
            "build",
            "--tag",
            "pppackage/runner-image",
            "-",
            stdin=PIPE,
            stdout=DEVNULL,
            stderr=None,
        )

        await process.communicate(dockerfile.encode("ascii"))
        return_code = await process.wait()

        stream_write_line(
            debug,
            "PPpackage-runner",
            writer,
            "SUCCESS" if return_code == 0 else "FAILURE",
        )

        if return_code != 0:
            return False

        await writer.drain()

        image = "pppackage/runner-image"
    else:
        return False

    args = [arg async for arg in stream_read_strings(debug, "PPpackage-runner", reader)]
    stdin_pipe_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runner", reader
    )
    stdout_pipe_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runner", reader
    )
    mount_source_paths = [
        container_path / mount_relative_path
        async for mount_relative_path in stream_read_relative_paths(
            debug, "PPpackage-runner", reader
        )
    ]
    mount_destination_paths = [
        Path(mount_destination_path_string)
        async for mount_destination_path_string in stream_read_strings(
            debug, "PPpackage-runner", reader
        )
    ]

    with stdin_pipe_path.open("r") as stdin_pipe, stdout_pipe_path.open(
        "w"
    ) as stdout_pipe:
        return_code = await (
            await create_subprocess_exec(
                "podman",
                "run",
                "--rm",
                "--interactive",
                *[
                    f"--mount=type=bind,source={mount_source_path},destination={mount_destination_path}"
                    for mount_source_path, mount_destination_path in zip(
                        mount_source_paths, mount_destination_paths
                    )
                ],
                image,
                *args,
                stdin=stdin_pipe,
                stdout=stdout_pipe,
                stderr=None,
            )
        ).wait()

        stream_write_line(
            debug,
            "PPpackage-runner",
            writer,
            "SUCCESS" if return_code == 0 else "FAILURE",
        )


async def handle_connection(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    containers_path: Path,
    bundle_path: Path,
    root_path: Path,
):
    container_id = await stream_read_string(debug, "PPpackage-runner", reader)
    container_path = containers_path / container_id

    while True:
        request = await stream_read_line(debug, "PPpackage-runner", reader)

        if reader.at_eof():
            break

        if request == "END":
            break
        elif request == "INIT":
            await handle_init(debug, reader, writer, containers_path, container_path)
        elif request == "COMMAND":
            result = await handle_command(
                debug, reader, writer, container_path, bundle_path, root_path
            )
            if not result:
                break
        elif request == "RUN":
            result = await handle_run(debug, reader, writer, container_path)
            if not result:
                break

        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def create_config(debug: bool, bundle_path: Path):
    if (bundle_path / config_relative_path).exists():
        return

    process_creation = create_subprocess_exec(
        "runc",
        "spec",
        "--rootless",
        "--bundle",
        str(bundle_path),
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=None,
    )

    await asubprocess_communicate(await process_creation, "Error in `runc spec`.", None)

    with edit_config(debug, bundle_path) as config:
        config["process"]["terminal"] = False
        config["root"]["readonly"] = False
        config["linux"]["uidMappings"][0]["hostID"] = getuid()
        config["linux"]["gidMappings"][0]["hostID"] = getgid()


async def run_server(
    debug: bool,
    containers_path: Path,
    bundle_path: Path,
    socket_path: Path,
    root_path: Path,
):
    try:
        async with await start_unix_server(
            lambda reader, writer: handle_connection(
                debug, reader, writer, containers_path, bundle_path, root_path
            ),
            socket_path,
        ) as server:
            await server.start_serving()

            loop = get_running_loop()

            future = loop.create_future()

            loop.add_signal_handler(SIGTERM, lambda: future.cancel())

            await future
    except CancelledError:
        pass
    finally:
        socket_path.unlink()


app = AsyncTyper()


@app.command()
async def main_command(daemon_path: Path, debug: bool = False):
    daemon_path = daemon_path.absolute()

    run_path = daemon_path / "run"

    socket_path = run_path / "PPpackage-runner.sock"

    containers_path = daemon_path / "containers"
    bundle_path = daemon_path / "bundle"

    try:
        with PidFile("PPpackage-runner", piddir=run_path):
            containers_path.mkdir(exist_ok=True)
            bundle_path.mkdir(exist_ok=True)

            await create_config(debug, bundle_path)

            with TemporaryDirectory() as root_path:
                await run_server(
                    debug, containers_path, bundle_path, socket_path, root_path
                )
    except PidFileAlreadyLockedError:
        print("PPpackage-runner is already running.", file=stderr)
        raise Exit(1)


def main():
    run(app, "PPpackage-runner")