from collections.abc import AsyncIterable, Iterable
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


class Writer(Protocol):
    async def write(self, data: memoryview) -> None:
        ...

    async def _dump_int(self, length: int) -> None:
        await self.write(memoryview(f"{length}\n".encode()))

        if _DEBUG_DUMP:
            print(f"dump length: {length}", file=stderr)

    async def _dump_bool(self, value: bool) -> None:
        value_string = _TRUE_STRING if value else "F"

        await self.write(memoryview((value_string + "\n").encode()))

        if _DEBUG_DUMP:
            print(f"dump bool: {value}", file=stderr)

    async def dump_bytes(self, output_bytes: memoryview) -> None:
        await self._dump_int(len(output_bytes))
        await self.write(output_bytes)

    async def dump_bytes_chunked(self, output_bytes: memoryview) -> None:
        async for chunk in self.dump_loop(chunk_bytes(output_bytes, 2**15)):
            await self.dump_bytes(chunk)

    async def dump_one(self, output: BaseModel | Any, loop=False) -> None:
        if loop:
            await self._dump_bool(True)

        output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

        output_json_string = output_wrapped.model_dump_json(
            indent=4 if _DEBUG_DUMP else None
        )

        output_json_bytes = output_json_string.encode()

        await self.dump_bytes(memoryview(output_json_bytes))

        if _DEBUG_DUMP:
            print(f"dump:\n{output_json_string}", file=stderr)

    async def dump_loop_end(self):
        await self._dump_bool(False)

        if _DEBUG_DUMP:
            print("loop}", file=stderr)

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
        async for output in self.dump_loop(outputs):
            await self.dump_one(output)

    async def dump_many_async(self, outputs: AsyncIterable[BaseModel | Any]) -> None:
        async for output in self.dump_loop_async(outputs):
            await self.dump_one(output)


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
