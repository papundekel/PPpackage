from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from PPpackage_runner.database import User
from PPpackage_runner.framework import framework
from PPpackage_utils.asyncio_stream import AsyncioWriter
from PPpackage_utils.http_stream import HTTPRequestReader
from PPpackage_utils.stream import Reader
from PPpackage_utils.utils import asubprocess_wait

from . import run


async def build_dockerfile(reader: Reader, tag: str) -> None:
    process = await create_subprocess_exec(
        "podman",
        "build",
        "--tag",
        tag,
        "-",
        stdin=PIPE,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    assert process.stdin is not None

    await reader.dump(AsyncioWriter(process.stdin))

    await asubprocess_wait(process, HTTPException(500, "Error in image pull."))


async def run_dockerfile(
    request: Request,
    user: Annotated[User, Depends(framework.get_user)],
    tag: str,
    args: Iterable[str],
    mount_source_relative_paths: Iterable[str],
    mount_destination_paths: Iterable[str],
    stdin_pipe_path: Path,
    stdout_pipe_path: Path,
):
    tag = "pppackage/runner-dockerfile-image"

    reader = HTTPRequestReader(request)

    await build_dockerfile(reader, tag)

    await run(
        user,
        tag,
        args,
        mount_source_relative_paths,
        mount_destination_paths,
        stdin_pipe_path,
        stdout_pipe_path,
    )
