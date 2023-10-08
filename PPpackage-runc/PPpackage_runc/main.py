from asyncio import (
    CancelledError,
    StreamReader,
    StreamWriter,
    create_subprocess_exec,
    get_running_loop,
    start_unix_server,
)
from contextlib import contextmanager
from json import load as json_load
from os import getgid, getuid
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL

from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.io import (
    stream_read_line,
    stream_read_relative_path,
    stream_read_string,
    stream_read_strings,
    stream_write_int,
    stream_write_string,
)
from PPpackage_utils.utils import (
    MyException,
    TemporaryDirectory,
    asubprocess_communicate,
    json_dump,
)


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
) -> None:
    if not container_path.exists():
        return False

    image_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runc", reader
    )

    command = await stream_read_string(debug, "PPpackage-runc", reader)
    args = [arg async for arg in stream_read_strings(debug, "PPpackage-runc", reader)]

    with edit_config(debug, bundle_path) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

    pipe_path = container_path / await stream_read_relative_path(
        debug, "PPpackage-runc", reader
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

    stream_write_int(debug, "PPpackage-runc", writer, return_code)

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
        "PPpackage-runc",
        writer,
        str(container_path.relative_to(containers_path)),
    )


async def handle_connection(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    containers_path: Path,
    bundle_path: Path,
    root_path: Path,
):
    container_id = await stream_read_string(debug, "PPpackage-runc", reader)
    container_path = containers_path / container_id

    while True:
        request = await stream_read_line(debug, "PPpackage-runc", reader)

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
    socket_path = run_path / "PPpackage-runc.sock"

    containers_path = daemon_path / "containers"

    bundle_path = daemon_path / "bundle"

    containers_path.mkdir(exist_ok=True)
    bundle_path.mkdir(exist_ok=True)

    await create_config(debug, bundle_path)

    with TemporaryDirectory() as root_path:
        await run_server(debug, containers_path, bundle_path, socket_path, root_path)


def main():
    run(app, "PPpackage-runc")
