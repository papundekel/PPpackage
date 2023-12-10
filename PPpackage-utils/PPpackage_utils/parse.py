from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncIterable, Iterable, Mapping
from inspect import isclass
from json import loads as json_loads
from sys import stderr
from typing import Annotated, Any, Generic, TypeVar, get_args

from PPpackage_utils.utils import MyException, frozendict
from pydantic import BaseModel, BeforeValidator, GetCoreSchemaHandler, RootModel
from pydantic.dataclasses import dataclass
from pydantic_core import CoreSchema, core_schema

_DEBUG_LOAD = False
_DEBUG_DUMP = False

Key = TypeVar("Key")
Value = TypeVar("Value")


class FrozenDictAnnotation(Generic[Key, Value]):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        key, value = get_args(source_type)

        return core_schema.no_info_after_validator_function(
            lambda x: frozendict(x),
            core_schema.dict_schema(
                handler.generate_schema(key), handler.generate_schema(value)
            ),
        )


def frozen_validator(value: Any) -> Any:
    if type(value) is dict:
        return frozendict(value)

    return value


FrozenAny = Annotated[Any, BeforeValidator(frozen_validator)]

ModelType = TypeVar("ModelType")


def load_object(Model: type[ModelType], input_json: Any) -> ModelType:
    ModelWrapped = (
        Model if isclass(Model) and issubclass(Model, BaseModel) else RootModel[Model]
    )

    input = ModelWrapped.model_validate(input_json)

    if isinstance(input, RootModel):
        return input.root
    else:
        return input  # type: ignore


def load_from_bytes(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode()

    if _DEBUG_LOAD:
        print(f"load:\n{input_json_string}", file=stderr)

    input_json = json_loads(input_json_string)

    return load_object(Model, input_json)


Options = Mapping[str, Any] | None


@dataclass(frozen=True)
class Product:
    name: str
    version: str
    product_id: str


@dataclass(frozen=True)
class PackageIDAndInfo:
    name: str
    product_id: str
    product_info: Any


@dataclass(frozen=True)
class BuildResult:
    name: str
    is_root: bool


@dataclass(frozen=True)
class ManagerAndName:
    manager: str
    name: str


@dataclass(frozen=True)
class Dependency(ManagerAndName):
    product_info: Any | None


@dataclass(frozen=True)
class Package:
    name: str
    version: str


@dataclass(frozen=True)
class ManagerRequirement:
    manager: str
    requirement: Any


@dataclass(frozen=True)
class ResolutionGraphNode:
    name: str
    version: str
    dependencies: Iterable[str]
    requirements: Iterable[ManagerRequirement]


@dataclass(frozen=True)
class ResolutionGraph:
    roots: Iterable[Iterable[str]]
    graph: Iterable[ResolutionGraphNode]


def _dump_int(debug: bool, writer: StreamWriter, length: int) -> None:
    writer.write(f"{length}\n".encode())

    if _DEBUG_DUMP:
        print(f"dump length: {length}", file=stderr)


_TRUE_STRING = "T"


def _dump_bool(debug: bool, writer: StreamWriter, value: bool) -> None:
    value_string = _TRUE_STRING if value else "F"

    writer.write((value_string + "\n").encode())

    if _DEBUG_DUMP:
        print(f"dump bool: {value}", file=stderr)


async def dump_bytes(
    debug: bool, writer: StreamWriter, output_bytes: memoryview
) -> None:
    _dump_int(debug, writer, len(output_bytes))
    writer.write(output_bytes)

    await writer.drain()


def chunk_bytes(data: memoryview, chunk_size: int) -> Iterable[memoryview]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


async def dump_bytes_chunked(
    debug: bool, writer: StreamWriter, output_bytes: memoryview
) -> None:
    async for chunk in dump_loop(debug, writer, chunk_bytes(output_bytes, 2**15)):
        await dump_bytes(debug, writer, chunk)


async def dump_one(
    debug: bool, writer: StreamWriter, output: BaseModel | Any, loop=False
) -> None:
    if loop:
        _dump_bool(debug, writer, True)

    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json(indent=4 if debug else None)

    output_json_bytes = output_json_string.encode()

    await dump_bytes(debug, writer, memoryview(output_json_bytes))

    if _DEBUG_DUMP:
        print(f"dump:\n{output_json_string}", file=stderr)


async def dump_loop_end(debug: bool, writer: StreamWriter):
    _dump_bool(debug, writer, False)
    await writer.drain()

    if _DEBUG_DUMP:
        print("loop}", file=stderr)


T = TypeVar("T")


async def dump_loop(
    debug: bool, writer: StreamWriter, iterable: Iterable[T]
) -> AsyncIterable[T]:
    if _DEBUG_DUMP:
        print("loop{", file=stderr)

    for obj in iterable:
        _dump_bool(debug, writer, True)
        yield obj

    await dump_loop_end(debug, writer)


async def dump_loop_async(
    debug: bool, writer: StreamWriter, iterable: AsyncIterable[T]
) -> AsyncIterable[T]:
    async for obj in iterable:
        _dump_bool(debug, writer, True)
        yield obj

    await dump_loop_end(debug, writer)


async def dump_many(
    debug: bool, writer: StreamWriter, outputs: Iterable[BaseModel | Any]
) -> None:
    async for output in dump_loop(debug, writer, outputs):
        await dump_one(debug, writer, output)


async def dump_many_async(
    debug: bool, writer: StreamWriter, outputs: AsyncIterable[BaseModel | Any]
) -> None:
    async for output in dump_loop_async(debug, writer, outputs):
        await dump_one(debug, writer, output)


async def _load_line(debug: bool, reader: StreamReader) -> str:
    line_bytes = await reader.readline()

    if len(line_bytes) == 0:
        raise MyException("Unexpected EOF.")

    line = line_bytes.decode().strip()

    return line


async def _load_int(debug: bool, reader: StreamReader) -> int:
    line = await _load_line(debug, reader)

    length = int(line)

    if _DEBUG_LOAD:
        print(f"load length: {length}", file=stderr)

    return length


async def _load_bool(debug: bool, reader: StreamReader) -> bool:
    line = await _load_line(debug, reader)

    value = line == _TRUE_STRING

    if _DEBUG_LOAD:
        print(f"load bool: {value}", file=stderr)

    return value


async def load_bytes(debug: bool, reader: StreamReader) -> bytes:
    length = await _load_int(debug, reader)

    if length == 0:
        raise MyException("Unexpected length 0.")

    return await reader.readexactly(length)


async def load_bytes_chunked(debug: bool, reader: StreamReader) -> memoryview:
    buffer = bytearray()

    async for _ in load_loop(debug, reader):
        buffer += await load_bytes(debug, reader)

    return memoryview(buffer)


async def load_one(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> ModelType:
    input_bytes = await load_bytes(debug, reader)

    return load_from_bytes(debug, Model, input_bytes)


async def load_loop(debug: bool, reader: StreamReader):
    while True:
        do_continue = await _load_bool(debug, reader)

        if not do_continue:
            break

        yield


async def load_many(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> AsyncIterable[ModelType]:
    async for _ in load_loop(debug, reader):
        yield await load_one(debug, reader, Model)
