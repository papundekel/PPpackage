from collections.abc import AsyncIterable, Iterable, Mapping

from fastapi import HTTPException
from fastapi.responses import StreamingResponse as BaseStreamingResponse
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
    headers: Mapping[str, str],
    generator: AsyncIterable[memoryview],
):
    if isinstance(generator, Iterable):
        generator_wrapped = (bytes(chunk) for chunk in generator)
    else:
        generator_wrapped = (bytes(chunk) async for chunk in generator)

    return BaseStreamingResponse(
        generator_wrapped,
        status_code=status_code,
        headers=headers,
        media_type="application/octet-stream",
    )
