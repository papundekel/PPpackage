from typing import Generic, TypeVar

from httpx import Response

from PPpackage.utils.http_stream import AsyncChunkReader


def HTTPResponseReader(response: Response):
    return AsyncChunkReader(memoryview(chunk) async for chunk in response.aiter_raw())


T = TypeVar("T")


class Result(Generic[T]):
    def __init__(self, *args: T):
        if len(args) == 0:
            self.value: T = None  # type: ignore
        else:
            self.value = args[0]
