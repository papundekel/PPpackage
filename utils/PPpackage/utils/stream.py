from collections.abc import AsyncIterable
from logging import getLogger
from typing import Any, Protocol

from pydantic import BaseModel

from .validation import validate_json, wrap_instance

_TRUE_STRING = "T"

logger = getLogger(__name__)


def _dump_int(length: int) -> memoryview:
    length_bytes = f"{length}\n".encode()

    return memoryview(length_bytes)


def _dump_bool(value: bool) -> memoryview:
    value_string = _TRUE_STRING if value else "F"

    bool_bytes = f"{value_string}\n".encode()

    return memoryview(bool_bytes)


async def dump_loop(
    iterable: AsyncIterable[AsyncIterable[memoryview]],
) -> AsyncIterable[memoryview]:
    async for obj in iterable:
        yield _dump_bool(True)
        async for chunk in obj:
            yield chunk

    yield _dump_bool(False)


async def dump_bytes(output_bytes: memoryview) -> AsyncIterable[memoryview]:
    yield _dump_int(len(output_bytes))
    yield output_bytes


async def chunk_bytes(data: memoryview, chunk_size: int) -> AsyncIterable[memoryview]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


async def dump_bytes_chunked(output_bytes: memoryview) -> AsyncIterable[memoryview]:
    async for chunk in dump_loop(
        dump_bytes(chunk) async for chunk in chunk_bytes(output_bytes, 2**15)
    ):
        yield chunk


async def dump_one(output: BaseModel | Any) -> AsyncIterable[memoryview]:
    output_wrapped = wrap_instance(output)

    output_json = output_wrapped.model_dump_json()

    output_json_bytes = output_json.encode()

    async for chunk in dump_bytes(memoryview(output_json_bytes)):
        yield chunk


async def dump_many(
    outputs: AsyncIterable[BaseModel | Any],
) -> AsyncIterable[memoryview]:
    async for chunk in dump_loop(dump_one(output) async for output in outputs):
        yield chunk


class Writer(Protocol):
    async def write(self, data: AsyncIterable[memoryview]) -> None: ...


class Reader(Protocol):
    async def readexactly(self, n: int) -> bytes: ...

    async def readuntil(self, separator: memoryview) -> bytes: ...

    def read(self) -> AsyncIterable[memoryview]: ...

    async def _readline(self) -> bytes:
        return await self.readuntil(memoryview(b"\n"))

    async def _load_line(self) -> str:
        line_bytes = await self._readline()

        line = str(line_bytes, "utf-8").strip()

        logger.debug(f"line: {line}")

        return line

    async def _load_int(self) -> int:
        line = await self._load_line()

        length = int(line)

        logger.debug(f"length: {length}")

        return length

    async def _load_bool(self) -> bool:
        line = await self._load_line()

        value = line == _TRUE_STRING

        logger.debug(f"bool: {value}")

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
