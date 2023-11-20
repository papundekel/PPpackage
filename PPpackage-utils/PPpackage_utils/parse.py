from asyncio import StreamWriter
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

from .utils import StreamReader

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


def model_validate_obj(
    debug: bool, Model: type[ModelType], input_json: Any
) -> ModelType:
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


def model_validate(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode("utf-8")

    input_json = json_loads(input_json_string)

    return model_validate_obj(False, Model, input_json)


def model_dump(debug: bool, output: BaseModel | Any) -> bytes:
    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_string = output_wrapped.model_dump_json(indent=4 if debug else None)

    output_json_bytes = output_json_string.encode("utf-8")

    return output_json_bytes


Requirement = TypeVar("Requirement")

Options = Mapping[str, Any] | None


class ResolveInput(BaseModel, Generic[Requirement]):
    options: Options
    requirements_list: Iterable[Iterable[Requirement]]


@dataclass(frozen=True)
class ProductBase:
    version: str
    product_id: str


@dataclass(frozen=True)
class Product(ProductBase):
    name: str


class GenerateInput(BaseModel):
    options: Options
    products: Iterable[Product]
    generators: Iterable[str]


@dataclass(frozen=True)
class FetchOutputValueBase:
    product_id: str
    product_info: Any


@dataclass(frozen=True)
class FetchOutputValue(FetchOutputValueBase):
    name: str


FetchOutput = Iterable[FetchOutputValue]


@dataclass(frozen=True)
class ManagerAndName:
    manager: str
    name: str


@dataclass(frozen=True)
class Dependency(ManagerAndName):
    product_info: Any | None


@dataclass(frozen=True)
class PackageWithDependencies:
    name: str
    version: str
    dependencies: Iterable[Dependency]


class FetchInput(BaseModel):
    options: Options
    packages: Iterable[PackageWithDependencies]


InstallInput = Iterable[Product]


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


def model_dump_stream(
    debug: bool, writer: StreamWriter, output: BaseModel | Any
) -> None:
    output_json_bytes = model_dump(debug, output)

    writer.write(f"{len(output_json_bytes)}\n".encode("utf-8"))
    writer.write(output_json_bytes)


@contextmanager
def models_dump_stream_end(
    debug: bool, writer: StreamWriter
) -> Generator[None, Any, None]:
    try:
        yield
    finally:
        writer.write("-1\n".encode("utf-8"))


def models_dump_stream(
    debug: bool, writer: StreamWriter, outputs: Iterable[BaseModel | Any]
) -> None:
    with models_dump_stream_end(debug, writer):
        for output in outputs:
            model_dump_stream(debug, writer, output)


async def models_dump_stream_async(
    debug: bool, writer: StreamWriter, outputs: AsyncIterable[BaseModel | Any]
) -> None:
    with models_dump_stream_end(debug, writer):
        async for output in outputs:
            model_dump_stream(debug, writer, output)


async def model_validate_stream_impl(
    debug: bool, reader: StreamReader, Model: type[ModelType], length: int
) -> ModelType:
    input_json_bytes = await reader.readexactly(length)

    return model_validate(debug, Model, input_json_bytes)


async def stream_read_length(debug: bool, reader: StreamReader) -> int:
    length = int((await reader.readline()).decode("utf-8"))

    return length


async def model_validate_stream(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> ModelType:
    length = await stream_read_length(debug, reader)

    return await model_validate_stream_impl(debug, reader, Model, length)


async def models_validate_stream(
    debug: bool, reader: StreamReader, Model: type[ModelType]
) -> AsyncIterable[ModelType]:
    while True:
        length = await stream_read_length(debug, reader)

        if length < 0:
            break

        yield await model_validate_stream_impl(debug, reader, Model, length)
