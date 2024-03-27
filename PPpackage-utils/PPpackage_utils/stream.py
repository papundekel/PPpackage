from collections.abc import AsyncIterable
from typing import Any, Protocol, TypeVar

from PPpackage_utils.validation import load_from_bytes
from pydantic import BaseModel, RootModel

_TRUE_STRING = "T"
T = TypeVar("T")


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
    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json()
    output_json_bytes = output_json_string.encode()

    async for chunk in dump_bytes(memoryview(output_json_bytes)):
        yield chunk


async def dump_many(
    outputs: AsyncIterable[BaseModel | Any],
) -> AsyncIterable[memoryview]:
    async for chunk in dump_loop(dump_one(output) async for output in outputs):
        yield chunk


class Writer(Protocol):
    async def write(self, data: memoryview) -> None: ...


ModelType = TypeVar("ModelType")


class Reader(Protocol):
    async def readexactly(self, n: int) -> memoryview: ...

    async def readuntil(self, separator: memoryview) -> memoryview: ...

    def read(self) -> AsyncIterable[memoryview]: ...

    async def _readline(self) -> memoryview:
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

    async def load_bytes(self) -> memoryview:
        length = await self._load_int()

        if length == 0:
            raise Exception("Unexpected length 0.")

        return await self.readexactly(length)

    async def load_bytes_chunked(self) -> memoryview:
        buffer = bytearray()

        async for _ in self.load_loop():
            buffer += await self.load_bytes()

        return memoryview(buffer)

    async def load_one(self, Model: type[ModelType]) -> ModelType:
        input_bytes = await self.load_bytes()

        return load_from_bytes(Model, input_bytes)

    async def load_loop(self):
        while True:
            do_continue = await self._load_bool()

            if not do_continue:
                break

            yield

    async def load_many(self, Model: type[ModelType]) -> AsyncIterable[ModelType]:
        async for _ in self.load_loop():
            yield await self.load_one(Model)

    async def dump_bytes_chunked(self, writer: Writer) -> None:
        async for _ in self.load_loop():
            await writer.write(await self.load_bytes())
