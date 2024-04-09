from asyncio import create_subprocess_exec
from collections.abc import AsyncIterable, Generator, Iterable, Mapping
from contextlib import asynccontextmanager, contextmanager
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Optional, TypeVar

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse as BaseStreamingResponse
from jinja2 import Template as Jinja2Template
from PPpackage_utils.http_stream import AsyncChunkReader
from PPpackage_utils.utils import TemporaryDirectory
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


def HTTP401Exception():
    return HTTPException(status_code=HTTP_401_UNAUTHORIZED)


def HTTP403Exception():
    return HTTPException(status_code=HTTP_403_FORBIDDEN)


def HTTP404Exception():
    return HTTPException(status_code=HTTP_404_NOT_FOUND)


def HTTP400Exception():
    return HTTPException(status_code=HTTP_400_BAD_REQUEST)


def StreamingResponse(
    status_code: int,
    generator: Iterable[memoryview] | AsyncIterable[memoryview],
):
    if isinstance(generator, Iterable):
        generator_wrapped = (bytes(chunk) for chunk in generator)
    else:
        generator_wrapped = (bytes(chunk) async for chunk in generator)

    return BaseStreamingResponse(
        generator_wrapped,
        status_code=status_code,
        media_type="application/octet-stream",
    )


def get_reader(request: Request):
    return AsyncChunkReader(memoryview(chunk) async for chunk in request.stream())


@contextmanager
def jinja_render_temp_file(
    template: Jinja2Template,
    template_context: Mapping[str, Any],
    suffix: Optional[str] = None,
) -> Generator[_TemporaryFileWrapper, Any, Any]:
    with NamedTemporaryFile(mode="w", suffix=suffix) as file:
        template.stream(**template_context).dump(file)

        file.flush()

        yield file


@asynccontextmanager
async def containerizer_subprocess_exec(
    url: str, *args, stdin: Any, stdout: Any, stderr: Any
):
    with (
        TemporaryDirectory() as empty_directory,
        NamedTemporaryFile() as containers_conf,
    ):
        yield await create_subprocess_exec(
            "podman-remote",
            "--url",
            url,
            *args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env={
                "CONTAINERS_CONF": containers_conf.name,
                "XDG_DATA_HOME": empty_directory,
                "XDG_CONFIG_HOME": empty_directory,
            },
        )
