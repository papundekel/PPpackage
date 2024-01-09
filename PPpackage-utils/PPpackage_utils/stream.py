from collections.abc import AsyncIterable, Iterable, Iterator
from sys import stderr
from typing import Any, Protocol, TypeVar

from PPpackage_utils.validation import load_from_bytes
from pydantic import BaseModel, RootModel

_DEBUG_LOAD = False
_DEBUG_DUMP = False


_TRUE_STRING = "T"
T = TypeVar("T")


def chunk_bytes(data: memoryview, chunk_size: int) -> Iterable[memoryview]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def _dump_int(length: int) -> memoryview:
    length_bytes = f"{length}\n".encode()

    if _DEBUG_DUMP:
        print(f"dump length: {length}", file=stderr)

    return memoryview(length_bytes)


def _dump_bool(value: bool) -> memoryview:
    value_string = _TRUE_STRING if value else "F"

    bool_bytes = (value_string + "\n").encode()

    if _DEBUG_DUMP:
        print(f"dump bool: {value}", file=stderr)

    return memoryview(bool_bytes)


def dump_bytes(output_bytes: memoryview) -> Iterable[memoryview]:
    yield _dump_int(len(output_bytes))
    yield output_bytes


def dump_loop_end():
    end_bytes = _dump_bool(False)

    if _DEBUG_DUMP:
        print("loop}", file=stderr)

    return end_bytes


def dump_loop(iterable: Iterable[Iterable[memoryview]]) -> Iterable[memoryview]:
    if _DEBUG_DUMP:
        print("loop{", file=stderr)

    for obj in iterable:
        yield _dump_bool(True)
        yield from obj

    yield dump_loop_end()


def dump_loop_simple(iterable: Iterable[memoryview]) -> Iterable[memoryview]:
    yield from dump_loop([iterable])


def dump_bytes_chunked(output_bytes: memoryview) -> Iterator[memoryview]:
    for chunk in dump_loop_simple(chunk_bytes(output_bytes, 2**15)):
        yield from dump_bytes(chunk)


def dump_one(output: BaseModel | Any, loop=False) -> Iterable[memoryview]:
    if loop:
        yield _dump_bool(True)

    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json(
        indent=4 if _DEBUG_DUMP else None
    )

    output_json_bytes = output_json_string.encode()

    yield from dump_bytes(memoryview(output_json_bytes))

    if _DEBUG_DUMP:
        print(f"dump:\n{output_json_string}", file=stderr)


def dump_many(outputs: Iterable[BaseModel | Any]) -> Iterable[memoryview]:
    yield from dump_loop(dump_one(output) for output in outputs)


async def dump_many_async(
    outputs: AsyncIterable[BaseModel | Any],
) -> AsyncIterable[memoryview]:
    async for output in outputs:
        for chunk in dump_one(output):
            yield chunk


class Writer(Protocol):
    async def write(self, data: memoryview) -> None:
        ...

    async def _write_many(self, data: Iterable[memoryview]) -> None:
        for chunk in data:
            await self.write(chunk)

    async def _dump_bool(self, value: bool) -> None:
        await self.write(_dump_bool(value))

    async def dump_bytes(self, output_bytes: memoryview) -> None:
        await self._write_many(dump_bytes(output_bytes))

    async def dump_bytes_chunked(self, output_bytes: memoryview) -> None:
        await self._write_many(dump_bytes_chunked(output_bytes))

    async def dump_one(self, output: BaseModel | Any, loop=False) -> None:
        await self._write_many(dump_one(output, loop))

    async def dump_loop_end(self):
        await self.write(dump_loop_end())

    async def dump_loop(self, iterable: Iterable[T]) -> AsyncIterable[T]:
        if _DEBUG_DUMP:
            print("loop{", file=stderr)

        for obj in iterable:
            await self._dump_bool(True)
            yield obj

        await self.dump_loop_end()

    async def dump_loop_async(self, iterable: AsyncIterable[T]) -> AsyncIterable[T]:
        async for obj in iterable:
            await self._dump_bool(True)
            yield obj

        await self.dump_loop_end()

    async def dump_many(self, outputs: Iterable[BaseModel | Any]) -> None:
        await self._write_many(dump_many(outputs))

    async def dump_many_async(self, outputs: AsyncIterable[BaseModel | Any]) -> None:
        async for chunk in dump_many_async(outputs):
            await self.write(chunk)


ModelType = TypeVar("ModelType")


class Reader(Protocol):
    async def readexactly(self, n: int) -> memoryview:
        ...

    async def readuntil(self, separator: memoryview) -> memoryview:
        ...

    def read(self) -> AsyncIterable[memoryview]:
        ...

    async def _readline(self) -> memoryview:
        return await self.readuntil(memoryview(b"\n"))

    async def _load_line(self) -> str:
        line_bytes = await self._readline()

        line = str(line_bytes, "utf-8").strip()

        return line

    async def _load_int(self) -> int:
        line = await self._load_line()

        length = int(line)

        if _DEBUG_LOAD:
            print(f"load length: {length}", file=stderr)

        return length

    async def _load_bool(self) -> bool:
        line = await self._load_line()

        value = line == _TRUE_STRING

        if _DEBUG_LOAD:
            print(f"load bool: {value}", file=stderr)

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

    async def dump(self, writer: Writer) -> None:
        async for chunk in self.read():
            await writer.write(chunk)
