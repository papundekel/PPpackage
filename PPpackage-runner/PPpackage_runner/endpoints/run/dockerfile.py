from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE

from fastapi import HTTPException
from PPpackage_runner.database import User
from PPpackage_runner.utils import State
from PPpackage_utils.asyncio_stream import AsyncioWriter
from PPpackage_utils.stream import Reader, Writer
from PPpackage_utils.utils import asubprocess_wait
from starlette.datastructures import ImmutableMultiDict

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
    state: State,
    query_parameters: ImmutableMultiDict[str, str],
    user: User,
    reader: Reader,
    writer: Writer,
):
    tag = "pppackage/runner-dockerfile-image"

    await build_dockerfile(reader, tag)

    return await run(user, tag, query_parameters)
