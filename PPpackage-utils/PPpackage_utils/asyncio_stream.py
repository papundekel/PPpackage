from asyncio import StreamReader, StreamWriter
from asyncio import start_unix_server as base_start_unix_server
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import AsyncIterable

from PPpackage_utils.stream import Reader, Writer


class AsyncioReader(Reader):
    def __init__(self, reader: StreamReader):
        self._reader = reader

    async def readexactly(self, count: int) -> memoryview:
        return memoryview(await self._reader.readexactly(count))

    async def readuntil(self, separator: memoryview) -> memoryview:
        return memoryview(await self._reader.readuntil(separator))

    async def read(self) -> AsyncIterable[memoryview]:
        while True:
            chunk = await self._reader.read(4096)

            if len(chunk) == 0:
                break

            yield memoryview(chunk)


class AsyncioWriter(Writer):
    def __init__(self, writer: StreamWriter):
        self._writer = writer

    async def write(self, data: memoryview) -> None:
        self._writer.write(data)
        await self._writer.drain()


async def start_unix_server(
    client_connected_cb: Callable[[Reader, Writer], Awaitable[None]], socket_path: Path
):
    async def cb(reader: StreamReader, writer: StreamWriter) -> None:
        await client_connected_cb(AsyncioReader(reader), AsyncioWriter(writer))

    return await base_start_unix_server(cb, socket_path)
