from asyncio import create_subprocess_exec
from collections.abc import Iterable
from pathlib import Path

from fastapi import HTTPException
from PPpackage_runner.database import User
from PPpackage_utils.utils import asubprocess_wait


async def run(
    user: User,
    tag: str,
    args: Iterable[str],
    mount_source_relative_paths: Iterable[str],
    mount_destination_paths: Iterable[str],
    stdin_pipe_path: Path,
    stdout_pipe_path: Path,
):
    workdir_path = user.workdir_path

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
