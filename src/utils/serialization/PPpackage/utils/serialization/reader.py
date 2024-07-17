from collections.abc import AsyncIterable
from typing import Protocol

from PPpackage.utils.json.validate import validate_json

from .utils import _TRUE_STRING


class Reader(Protocol):
    async def readexactly(self, n: int) -> bytes: ...

    async def readuntil(self, separator: memoryview) -> bytes: ...

    def read(self) -> AsyncIterable[memoryview]: ...

    async def _readline(self) -> bytes:
        return await self.readuntil(memoryview(b"\n"))

    async def _load_line(self) -> str:
        line_bytes = await self._readline()

        line = str(line_bytes, "utf-8").strip()

        return line

    async def _load_int(self) -> int:
        line = await self._load_line()

        length = int(line)

        return length

    async def _load_bool(self) -> bool:
        line = await self._load_line()

        value = line == _TRUE_STRING

        return value

    async def load_bytes(self) -> bytes:
        length = await self._load_int()

        if length == 0:
            raise Exception("Unexpected length 0.")

        return await self.readexactly(length)

    async def load_bytes_chunked(self) -> memoryview:
        buffer = bytearray()

        async for _ in self.load_loop():
            buffer += await self.load_bytes()

        return memoryview(buffer)

    async def load_one[T](self, Model: type[T]) -> T:
        input_bytes = await self.load_bytes()

        input = validate_json(Model, input_bytes)

        return input

    async def load_loop(self):
        while True:
            do_continue = await self._load_bool()

            if not do_continue:
                break

            yield

    async def load_many[T](self, Model: type[T]) -> AsyncIterable[T]:
        async for _ in self.load_loop():
            yield await self.load_one(Model)
