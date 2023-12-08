from asyncio import StreamReader, StreamWriter, create_subprocess_exec
from asyncio.subprocess import PIPE
from contextlib import asynccontextmanager, contextmanager
from functools import partial
from json import dump as json_dump
from json import load as json_load
from os import getgid, getuid
from pathlib import Path
from subprocess import DEVNULL
from typing import Tuple
from typing import cast as type_cast

from PPpackage_utils.parse import dump_one, load_many, load_one
from PPpackage_utils.submanager import run_server
from PPpackage_utils.utils import (
    ImageType,
    MyException,
    RunnerRequestType,
    TemporaryDirectory,
    asubprocess_wait,
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
):
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

            await process.communicate(dockerfile.encode("utf-8"))
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
                stderr=None,
            )
        ).wait()

    await dump_one(debug, writer, return_code == 0)

    return True


async def handle_connection(
    workdirs_path: Path,
    bundle_path: Path,
    root_path: Path,
    debug: bool,
    reader: StreamReader,
    writer: StreamWriter,
):
    with TemporaryDirectory(workdirs_path) as workdir_path:
        await dump_one(debug, writer, workdir_path.relative_to(workdirs_path))

        while True:
            request = await load_one(debug, reader, RunnerRequestType)

            if reader.at_eof():
                break

            match request:
                case RunnerRequestType.END:
                    break

                case RunnerRequestType.COMMAND:
                    await handle_command(
                        debug,
                        reader,
                        writer,
                        workdir_path,
                        bundle_path,
                        root_path,
                    )

                case RunnerRequestType.RUN:
                    result = await handle_run(debug, reader, writer, workdir_path)

                    if not result:
                        break

            await writer.drain()

        writer.close()
        await writer.wait_closed()


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

    await asubprocess_wait(await process_creation, MyException("Error in `runc spec`."))

    with edit_config(debug, bundle_path) as config:
        config["process"]["terminal"] = False
        config["root"]["readonly"] = False
        config["linux"]["uidMappings"][0]["hostID"] = getuid()
        config["linux"]["gidMappings"][0]["hostID"] = getgid()


program_name = "PPpackage-runner"


@asynccontextmanager
async def lifetime(workdirs_path: Path, debug: bool):
    with TemporaryDirectory() as bundle_path, TemporaryDirectory() as root_path:
        await create_config(debug, bundle_path)

        yield partial(handle_connection, workdirs_path, bundle_path, root_path)


async def main(debug: bool, run_path: Path, workdirs_path: Path):
    await run_server(debug, program_name, run_path, partial(lifetime, workdirs_path))
