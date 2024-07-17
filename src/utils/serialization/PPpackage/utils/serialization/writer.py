from collections.abc import AsyncIterable, Iterable
from typing import Any, Protocol

from pydantic import BaseModel

from PPpackage.utils.json.utils import wrap_instance
from PPpackage.utils.json.validate import validate_json

from .utils import _TRUE_STRING


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


async def dump_one(output: BaseModel | Any) -> AsyncIterable[memoryview]:
    output_wrapped = wrap_instance(output)

    output_json = output_wrapped.model_dump_json()

    output_json_bytes = output_json.encode()

    yield _dump_int(len(output_json_bytes))

    yield memoryview(output_json_bytes)


async def dump_many(
    outputs: AsyncIterable[BaseModel | Any],
) -> AsyncIterable[memoryview]:
    async for output in outputs:
        yield _dump_bool(True)

        async for chunk in dump_one(output):
            yield chunk

    yield _dump_bool(False)


class Writer(Protocol):
    async def write(self, data: AsyncIterable[memoryview]) -> None: ...
