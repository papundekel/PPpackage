from asyncio import create_subprocess_exec
from pathlib import Path

from fastapi import HTTPException
from PPpackage_runner.database import User
from PPpackage_utils.server import HTTP400Exception
from PPpackage_utils.utils import asubprocess_wait
from starlette.datastructures import ImmutableMultiDict


async def run(user: User, tag: str, query_parameters: ImmutableMultiDict[str, str]):
    workdir_path = user.workdir_path

    args = query_parameters.getlist("args")
    mount_source_relative_paths = query_parameters.getlist(
        "mount_source_relative_paths"
    )
    mount_destination_paths = query_parameters.getlist("mount_destination_paths")

    try:
        stdin_pipe_path = Path(query_parameters["stdin_pipe_path"])
        stdout_pipe_path = Path(query_parameters["stdout_pipe_path"])
    except KeyError:
        raise HTTP400Exception()

    with stdin_pipe_path.open("r") as stdin_pipe, stdout_pipe_path.open(
        "w"
    ) as stdout_pipe:
        process = await create_subprocess_exec(
            "podman",
            "run",
            "--rm",
            "--interactive",
            *[
                "--mount=type=bind,"
                f"source={workdir_path / mount_source_relative_path},"
                f"destination={mount_destination_path}"
                for mount_source_relative_path, mount_destination_path in zip(
                    mount_source_relative_paths, mount_destination_paths
                )
            ],
            tag,
            *args,
            stdin=stdin_pipe,
            stdout=stdout_pipe,
            stderr=None,
        )

    await asubprocess_wait(process, HTTPException(500, "Error in image pull."))
