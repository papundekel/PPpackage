from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncIterable, Generator, Iterable, Mapping
from contextlib import contextmanager
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


def load_bytes(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode()

    if False:
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


def _dump_length(debug: bool, writer: StreamWriter, length: int) -> None:
    writer.write(f"{length}\n".encode())

    if False:
        print(f"dump length: {length}", file=stderr)


async def dump_one(debug: bool, writer: StreamWriter, output: BaseModel | Any) -> None:
    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json(indent=4 if debug else None)

    output_json_bytes = output_json_string.encode()

    _dump_length(debug, writer, len(output_json_bytes))
    writer.write(output_json_bytes)

    if False:
        print(f"dump:\n{output_json_string}", file=stderr)

    await writer.drain()


async def dump_none(debug: bool, writer: StreamWriter) -> None:
    _dump_length(debug, writer, 0)

    await writer.drain()


@contextmanager
def dump_many_end(debug: bool, writer: StreamWriter) -> Generator[None, Any, None]:
    try:
        yield
    finally:
        _dump_length(debug, writer, -1)


async def dump_many(
    debug: bool, writer: StreamWriter, outputs: Iterable[BaseModel | Any]
) -> None:
    with dump_many_end(debug, writer):
        for output in outputs:
            await dump_one(debug, writer, output)


async def dump_many_async(
    debug: bool, writer: StreamWriter, outputs: AsyncIterable[BaseModel | Any]
) -> None:
    with dump_many_end(debug, writer):
        async for output in outputs:
            await dump_one(debug, writer, output)


async def load_impl(
    debug: bool, reader: StreamReader, Model: type[ModelType], length: int
) -> ModelType:
    input_json_bytes = await reader.readexactly(length)

    return load_bytes(debug, Model, input_json_bytes)


async def _load_length(debug: bool, reader: StreamReader) -> int:
    line_bytes = await reader.readline()

    if len(line_bytes) == 0:
        raise MyException("Unexpected EOF.")

    length = int(line_bytes.decode().strip())

    if False:
        print(f"load length: {length}", file=stderr)

    return length


async def load_one(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> ModelType:
    length = await _load_length(debug, reader)

    return await load_impl(debug, reader, Model, length)


async def load_many_helper(debug: bool, reader: StreamReader):
    while True:
        length = await _load_length(debug, reader)

        if length < 0:
            break

        yield length


async def load_many(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> AsyncIterable[ModelType]:
    async for length in load_many_helper(debug, reader):
        yield await load_impl(debug, reader, Model, length)
