from asyncio import IncompleteReadError
from collections.abc import AsyncIterable

from .reader import Reader


class ChunkReader(Reader):
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

    def _pop_buffer(self, count: int) -> bytes:
        chunk = self._buffer[:count]
        del self._buffer[:count]

        return chunk

    async def readexactly(self, count: int) -> bytes:
        while len(self._buffer) < count:
            await self._fill_buffer()

        return self._pop_buffer(count)

    async def readuntil(self, separator: memoryview) -> bytes:
        start = 0
        while (index := self._buffer.find(separator, start)) == -1:
            start = len(self._buffer)
            await self._fill_buffer()

        return self._pop_buffer(index + len(separator))

    def read(self) -> AsyncIterable[memoryview]:
        return self._iterator
