#!/usr/bin/env python

import json
from asyncio import StreamReader, StreamWriter, create_subprocess_exec, get_running_loop
from asyncio import run as asyncio_run
from asyncio import start_unix_server
from collections.abc import Iterable
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from subprocess import DEVNULL
from sys import stderr

from daemon import DaemonContext
from daemon.pidfile import PIDLockFile
from lockfile import AlreadyLocked
from typer import Exit, Typer

from PPpackage_utils import (
    asubprocess_communicate,
    stream_read_line,
    stream_read_relative_path,
    stream_read_string,
    stream_read_strings,
    stream_write_int,
    stream_write_string,
)


@contextmanager
def edit_json_file(path: Path, debug: bool):
    with path.open("r+") as file:
        data = json.load(file)

        try:
            yield data
        finally:
            file.seek(0)
            file.truncate()

            json.dump(data, file, indent=4 if debug else None)


def edit_config(bundle_path: Path, debug: bool):
    return edit_json_file(bundle_path / "config.json", debug)


async def handle_command(
    debug: bool,
    container_path: Path,
    bundle_path: Path,
    reader: StreamReader,
    writer: StreamWriter,
) -> None:
    image_path = container_path / await stream_read_relative_path(reader)

    command = await stream_read_string(reader)
    args = [arg async for arg in stream_read_strings(reader)]

    with edit_config(bundle_path, debug) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

    pipe_path = container_path / await stream_read_relative_path(reader)

    with pipe_path.open("r") as pipe:
        process = await create_subprocess_exec(
            "runc",
            "run",
            "--bundle",
            str(bundle_path),
            "PPpackage-container",
            stdin=pipe,
            stdout=DEVNULL,
            stderr=None,
        )

        return_code = await process.wait()

    stream_write_int(writer, return_code)


def handle_init(container_path: Path, reader: StreamReader, writer: StreamWriter):
    stream_write_string(writer, str(container_path.absolute()))


async def handle_connection(
    debug: bool,
    containers_path: Path,
    bundle_path: Path,
    reader: StreamReader,
    writer: StreamWriter,
):
    container_id = await stream_read_string(reader)

    container_path = containers_path / container_id

    container_path.mkdir(exist_ok=True)

    while True:
        request = await stream_read_line(reader)

        if request == "END":
            break
        elif request == "INIT":
            handle_init(container_path, reader, writer)
        elif request == "COMMAND":
            await handle_command(debug, container_path, bundle_path, reader, writer)

        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def create_config(debug: bool, bundle_path: Path):
    bundle_path.mkdir(exist_ok=True)

    if (bundle_path / "config.json").exists():
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

    with edit_config(bundle_path, debug) as config:
        config["process"]["terminal"] = False
        config["root"]["readonly"] = False


async def run_server(
    debug: bool, containers_path: Path, bundle_path: Path, socket_path: Path
):
    try:
        async with await start_unix_server(
            partial(handle_connection, debug, containers_path, bundle_path), socket_path
        ) as server:
            await server.start_serving()
            await get_running_loop().create_future()
    finally:
        socket_path.unlink()


async def daemon(debug: bool, daemon_path: Path):
    containers_path = daemon_path / "containers"
    bundle_path = daemon_path / "bundle"
    socket_path = daemon_path / "PPpackage-runc.sock"

    containers_path.mkdir(exist_ok=True)
    await create_config(debug, bundle_path)

    await run_server(debug, containers_path, bundle_path, socket_path)


app = Typer()


@app.command()
def main(daemon_path: Path, debug: bool = False):
    daemon_path = daemon_path.absolute()
    pidfile_path = daemon_path / "PPpackage-runc.pid"

    pidfile = PIDLockFile(pidfile_path)
    try:
        with DaemonContext(pidfile=pidfile, stderr=stderr):
            asyncio_run(daemon(debug, daemon_path))
    except AlreadyLocked:
        print(f"Daemon already running. PID file: {pidfile_path}", file=stderr)
        raise Exit(1)


if __name__ == "__main__":
    app()
