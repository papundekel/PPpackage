from asyncio import StreamReader, StreamWriter
from typing import AsyncIterable

from .reader import Reader
from .writer import Writer


class AsyncioReader(Reader):
    def __init__(self, reader: StreamReader):
        self._reader = reader

    async def readexactly(self, count: int) -> bytes:
        return await self._reader.readexactly(count)

    async def readuntil(self, separator: memoryview) -> bytes:
        return await self._reader.readuntil(separator)

    async def read(self) -> AsyncIterable[memoryview]:
        while True:
            chunk = await self._reader.read(4096)

            if len(chunk) == 0:
                break

            yield memoryview(chunk)


class AsyncioWriter(Writer):
    def __init__(self, writer: StreamWriter):
        self._writer = writer

    async def write(self, data: AsyncIterable[memoryview]) -> None:
        async for chunk in data:
            self._writer.write(chunk)
        await self._writer.drain()
