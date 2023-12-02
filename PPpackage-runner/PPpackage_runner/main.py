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
from json import dump as json_dump
from json import load as json_load
from os import getgid, getuid
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL
from sys import stderr
from typing import Tuple
from typing import cast as type_cast

from pid import PidFile, PidFileAlreadyLockedError
from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.parse import dump_one, load_many, load_one
from PPpackage_utils.utils import (
    ImageType,
    RunnerRequestType,
    TemporaryDirectory,
    asubprocess_wait,
    wipe_directory,
)
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

    image_path = container_path / await load_one(debug, reader, Path)

    command = await load_one(debug, reader, str)
    args = [arg async for arg in load_many(debug, reader, str)]

    with edit_config(debug, bundle_path) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

    pipe_path = container_path / await load_one(debug, reader, Path)

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
            stderr=DEVNULL,
        )

        return_code = await process.wait()

    await dump_one(debug, writer, return_code)

    return True


async def handle_init(
    debug,
    reader: StreamReader,
    writer: StreamWriter,
    workdirs_path: Path,
    container_workdir_path: Path,
):
    container_workdir_path.mkdir(exist_ok=True)

    await dump_one(debug, writer, container_workdir_path.relative_to(workdirs_path))


async def pull_image(
    debug: bool, reader: StreamReader, image_type: ImageType
) -> Tuple[bool, str | None]:
    match image_type:
        case ImageType.TAG:
            image = await load_one(debug, reader, str)
            return True, image

        case ImageType.DOCKERFILE:
            dockerfile = await load_one(debug, reader, str)

            process = await create_subprocess_exec(
                "podman",
                "build",
                "--tag",
                "pppackage/runner-image",
                "-",
                stdin=PIPE,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )

            await process.communicate(dockerfile.encode("ascii"))
            return_code = await process.wait()

            return return_code == 0, "pppackage/runner-image"


async def handle_run(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    container_workdir_path: Path,
) -> bool:
    image_type = await load_one(debug, reader, ImageType)

    success, image = await pull_image(debug, reader, image_type)

    await dump_one(debug, writer, success)

    if not success:
        return False

    image = type_cast(str, image)

    args = [arg async for arg in load_many(debug, reader, str)]

    stdin_pipe_path = container_workdir_path / await load_one(debug, reader, Path)

    stdout_pipe_path = container_workdir_path / await load_one(debug, reader, Path)

    mount_source_paths = [
        container_workdir_path / mount_relative_path
        async for mount_relative_path in load_many(debug, reader, Path)
    ]

    mount_destination_paths = [
        Path(mount_destination_path_string)
        async for mount_destination_path_string in load_many(debug, reader, str)
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
                stderr=DEVNULL,
            )
        ).wait()

    await dump_one(debug, writer, return_code == 0)

    return True


async def handle_connection(
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
    workdirs_path: Path,
    bundle_path: Path,
    root_path: Path,
):
    container_id = await load_one(debug, reader, str)
    container_workdir_path = workdirs_path / container_id

    while True:
        request = await load_one(debug, reader, RunnerRequestType)

        if reader.at_eof():
            break

        match request:
            case RunnerRequestType.END:
                break

            case RunnerRequestType.INIT:
                await handle_init(
                    debug, reader, writer, workdirs_path, container_workdir_path
                )

            case RunnerRequestType.COMMAND:
                result = await handle_command(
                    debug,
                    reader,
                    writer,
                    container_workdir_path,
                    bundle_path,
                    root_path,
                )

                if not result:
                    break

            case RunnerRequestType.RUN:
                result = await handle_run(debug, reader, writer, container_workdir_path)

                if not result:
                    break

        await writer.drain()

    writer.close()
    await writer.wait_closed()

    wipe_directory(container_workdir_path)


async def create_config(debug: bool, bundle_path: Path):
    process_creation = create_subprocess_exec(
        "runc",
        "spec",
        "--rootless",
        "--bundle",
        str(bundle_path),
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    await asubprocess_wait(await process_creation, "Error in `runc spec`.")

    with edit_config(debug, bundle_path) as config:
        config["process"]["terminal"] = False
        config["root"]["readonly"] = False
        config["linux"]["uidMappings"][0]["hostID"] = getuid()
        config["linux"]["gidMappings"][0]["hostID"] = getgid()


async def run_server(
    debug: bool,
    workdirs_path: Path,
    bundle_path: Path,
    socket_path: Path,
    root_path: Path,
):
    try:
        async with await start_unix_server(
            lambda reader, writer: handle_connection(
                debug,
                reader,
                writer,
                workdirs_path,
                bundle_path,
                root_path,
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
async def main_command(run_path: Path, workdirs_path: Path, debug: bool = False):
    socket_path = run_path / "PPpackage-runner.sock"

    try:
        with (
            PidFile("PPpackage-runner", piddir=run_path),
            TemporaryDirectory() as bundle_path,
            TemporaryDirectory() as runc_root_path,
        ):
            await create_config(debug, bundle_path)

            await run_server(
                debug,
                workdirs_path,
                bundle_path,
                socket_path,
                runc_root_path,
            )
    except PidFileAlreadyLockedError:
        print("PPpackage-runner is already running.", file=stderr)
        raise Exit(1)


def main():
    run(app, "PPpackage-runner")
