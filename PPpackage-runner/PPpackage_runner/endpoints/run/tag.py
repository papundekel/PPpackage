from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from PPpackage_runner.database import User
from PPpackage_runner.framework import framework

from . import run


async def run_tag(
    user: Annotated[User, Depends(framework.get_user)],
    tag: str,
    args: Iterable[str],
    mount_source_relative_paths: Iterable[str],
    mount_destination_paths: Iterable[str],
    stdin_pipe_path: Path,
    stdout_pipe_path: Path,
):
    await run(
        user,
        tag,
        args,
        mount_source_relative_paths,
        mount_destination_paths,
        stdin_pipe_path,
        stdout_pipe_path,
    )
