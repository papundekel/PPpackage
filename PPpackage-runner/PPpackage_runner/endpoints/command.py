from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from pathlib import Path

from PPpackage_runner.database import User
from PPpackage_runner.utils import State, edit_config
from PPpackage_utils.stream import Reader, Writer
from starlette.datastructures import ImmutableMultiDict


async def command(
    state: State,
    query_parameters: ImmutableMultiDict[str, str],
    user: User,
    reader: Reader,
    writer: Writer,
):
    workdir_path = user.workdir_path

    image_relative_path = query_parameters["image_relative_path"]

    image_path = workdir_path / image_relative_path

    command = query_parameters["command"]
    args = query_parameters.getlist("args")

    with edit_config(state.bundle_path) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

    pipe_relative_path = Path(query_parameters["query_relative_path"])
    pipe_path = workdir_path / pipe_relative_path

    with pipe_path.open("r") as pipe:
        process = await create_subprocess_exec(
            "crun",
            "--root",
            str(state.crun_root_path),
            "run",
            "--bundle",
            str(state.bundle_path),
            "PPpackage-container",
            stdin=pipe,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )

        return_code = await process.wait()

    await writer.dump_one(return_code)
