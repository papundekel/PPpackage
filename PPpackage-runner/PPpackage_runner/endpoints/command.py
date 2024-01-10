from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from PPpackage_runner.database import User
from PPpackage_runner.framework import framework
from PPpackage_runner.utils import State, edit_config
from PPpackage_utils.stream import Writer


async def command(
    state: Annotated[State, Depends(framework.get_state)],
    user: Annotated[User, Depends(framework.get_user)],
    image_relative_path: Path,
    pipe_relative_path: Path,
    command: str,
    args: list[str],
):
    workdir_path = user.workdir_path

    image_path = workdir_path / image_relative_path

    with edit_config(state.bundle_path) as config:
        config["process"]["args"] = [command, *args[1:]]
        config["root"]["path"] = str(image_path.absolute())

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

    return return_code
