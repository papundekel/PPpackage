from asyncio import IncompleteReadError
from collections.abc import AsyncIterable

from fastapi import Request
from httpx import Response
from PPpackage_utils.queue import Queue, queue_iterate
from PPpackage_utils.stream import Reader, Writer


class AsyncChunkReader(Reader):
    def __init__(self, chunks: AsyncIterable[memoryview]):
        self._buffer = bytearray()
        self._iterator = aiter(chunks)

    async def _iteration(self) -> memoryview | None:
        try:
            return await anext(self._iterator)
        except StopAsyncIteration:
            return None

    async def _fill_buffer(self) -> None:
        chunk = await self._iteration()

        if chunk is None:
            raise IncompleteReadError(self._buffer, 0)

        self._buffer += chunk

    def _pop_buffer(self, count: int) -> memoryview:
        chunk = self._buffer[:count]
        del self._buffer[:count]

        return memoryview(chunk)

    async def readexactly(self, count: int) -> memoryview:
        while len(self._buffer) < count:
            await self._fill_buffer()

        return self._pop_buffer(count)

    async def readuntil(self, separator: memoryview) -> memoryview:
        start = 0
        while (index := self._buffer.find(separator, start)) == -1:
            start = len(self._buffer)
            await self._fill_buffer()

        return self._pop_buffer(index + len(separator))

    async def read(self) -> AsyncIterable[memoryview]:
        return self._iterator


def HTTPRequestReader(request: Request):
    return AsyncChunkReader(memoryview(chunk) async for chunk in request.stream())


def HTTPResponseReader(response: Response):
    return AsyncChunkReader(memoryview(chunk) async for chunk in response.aiter_raw())


class HTTPWriter(Writer):
    def __init__(self):
        self._queue = Queue[memoryview]()

    async def write(self, data: memoryview) -> None:
        await self._queue.put(data)

    def iterate(self):
        return queue_iterate(self._queue)
