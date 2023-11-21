from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncGenerator, AsyncIterable, Iterable, Mapping
from inspect import isclass
from json import dumps as json_dumps
from json import loads as json_loads
from sys import stderr
from typing import Annotated, Any, Generic, TypeVar, get_args

from PPpackage_utils.utils import MyException, frozendict
from pydantic import (
    BaseModel,
    BeforeValidator,
    GetCoreSchemaHandler,
    RootModel,
    ValidationError,
)
from pydantic.dataclasses import dataclass
from pydantic_core import CoreSchema, core_schema

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

    try:
        input = ModelWrapped.model_validate(input_json)

        if isinstance(input, RootModel):
            return input.root
        else:
            return input  # type: ignore

    except ValidationError as e:
        input_json_string = json_dumps(input_json, indent=4)

        raise MyException(f"Model validation failed:\n{e}\n{input_json_string}")


def load_from_bytes(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode()

    if True:
        print(f"load:\n{input_json_string}", file=stderr)

    input_json = json_loads(input_json_string)

    return load_object(Model, input_json)


Options = Mapping[str, Any] | None


@dataclass(frozen=True)
class ProductBase:
    version: str
    product_id: str


@dataclass(frozen=True)
class Product(ProductBase):
    name: str


@dataclass(frozen=True)
class FetchOutputValueBase:
    product_id: str
    product_info: Any


@dataclass(frozen=True)
class FetchOutputValue(FetchOutputValueBase):
    name: str


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

    if True:
        print(f"dump length: {length}", file=stderr)


async def dump_one(debug: bool, writer: StreamWriter, output: BaseModel | Any) -> None:
    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json(indent=4 if debug else None)

    output_json_bytes = output_json_string.encode()

    _dump_int(debug, writer, len(output_json_bytes))
    writer.write(output_json_bytes)

    if True:
        print(f"dump:\n{output_json_string}", file=stderr)

    await writer.drain()


async def dump_many_end(debug: bool, writer: StreamWriter):
    _dump_int(debug, writer, 0)
    await writer.drain()


async def dump_loop(debug: bool, writer: StreamWriter, iterable: Iterable):
    for obj in iterable:
        _dump_int(debug, writer, 1)
        yield obj

    await dump_many_end(debug, writer)


async def dump_loop_async(debug: bool, writer: StreamWriter, iterable: AsyncIterable):
    async for obj in iterable:
        _dump_int(debug, writer, 1)
        yield obj  # type: ignore

    await dump_many_end(debug, writer)


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


async def _load_int(debug: bool, reader: StreamReader) -> int:
    line_bytes = await reader.readline()

    if len(line_bytes) == 0:
        raise MyException("Unexpected EOF.")

    length = int(line_bytes.decode().strip())

    if True:
        print(f"load length: {length}", file=stderr)

    return length


async def load_bytes(debug: bool, reader: StreamReader) -> bytes:
    length = await _load_int(debug, reader)

    if length == 0:
        raise MyException("Unexpected length 0.")

    return await reader.readexactly(length)


async def load_one(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> ModelType:
    input_bytes = await load_bytes(debug, reader)

    return load_from_bytes(debug, Model, input_bytes)


async def load_many_loop(debug: bool, reader: StreamReader):
    while True:
        do_continue = await _load_int(debug, reader)

        if do_continue == 0:
            break

        yield


async def load_many(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> AsyncIterable[ModelType]:
    async for _ in load_many_loop(debug, reader):
        yield await load_one(debug, reader, Model)
