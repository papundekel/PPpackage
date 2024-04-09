from collections.abc import AsyncIterable, Generator, Iterable, Mapping
from contextlib import contextmanager
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse as BaseStreamingResponse
from jinja2 import Template as Jinja2Template
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from PPpackage.utils.http_stream import AsyncChunkReader


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
