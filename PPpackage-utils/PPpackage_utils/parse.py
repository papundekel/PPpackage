import json
from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncIterable, Hashable, Mapping, Set
from contextlib import contextmanager
from email import contentmanager
from lib2to3.pytree import Base
from re import M
from sys import stderr
from textwrap import indent
from typing import Annotated, Any, Generic, Sequence, TypeGuard, TypeVar, get_args

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


def model_validate_obj(
    debug: bool, Model: type[ModelType], input_json: Any
) -> ModelType:
    ModelWrapped = Model if issubclass(Model, BaseModel) else RootModel[ModelType]

    try:
        input = ModelWrapped.model_validate(input_json)

        if isinstance(input, RootModel):
            return input.root
        else:
            return input

    except ValidationError as e:
        input_json_string = json.dumps(input_json, indent=4 if debug else None)

        raise MyException(f"Model validation failed:\n{e}\n{input_json_string}")


def model_validate(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode("utf-8")

    input_json = json.loads(input_json_string)

    return model_validate_obj(debug, Model, input_json)


def model_dump(debug: bool, output: BaseModel) -> bytes:
    output_json_string = output.model_dump_json(indent=4 if debug else None)

    if debug:
        print(f"DEBUG model_dump:\n{output_json_string}", file=stderr)

    output_json_bytes = output_json_string.encode("utf-8")

    return output_json_bytes


Requirement = TypeVar("Requirement")


class ResolveInput(BaseModel, Generic[Requirement]):
    requirements_list: Sequence[Set[Requirement]]
    options: Mapping[str, Any] | None


class GenerateInputPackagesValue(BaseModel):
    version: str
    product_id: str


class GenerateInput(BaseModel):
    generators: Set[str]
    packages: Mapping[str, GenerateInputPackagesValue]
    options: Mapping[str, Any] | None


class FetchOutputValue(BaseModel):
    product_id: str
    product_info: Any


FetchOutput = RootModel[Mapping[str, FetchOutputValue]]


class FetchInputPackageValue(BaseModel):
    version: str
    dependencies: Mapping[str, Set[str]]


class FetchInput(BaseModel):
    packages: Mapping[str, FetchInputPackageValue]
    product_infos: Mapping[str, Mapping[str, Any]]
    options: Mapping[str, Any] | None


@dataclass(frozen=True)
class Product:
    package: str
    version: str
    product_id: str


InstallInput = RootModel[Set[Product]]


FrozenDictAnnotated = Annotated[
    frozendict[Key, Value], FrozenDictAnnotation[Key, Value]()
]


@dataclass(frozen=True)
class ResolutionGraphNodeValue:
    version: str
    dependencies: Set[str]
    requirements: FrozenDictAnnotated[str, frozenset[Hashable]]


@dataclass(frozen=True)
class ResolutionGraph:
    roots: tuple[Set[str], ...]
    graph: FrozenDictAnnotated[str, ResolutionGraphNodeValue]


def model_dump_stream(
    debug: bool, writer: StreamWriter, output: BaseModel | Any
) -> None:
    output_wrapped = output if isinstance(output, BaseModel) else RootModel(output)

    output_json_bytes = model_dump(debug, output_wrapped)

    writer.write(f"{len(output_json_bytes)}\n".encode("utf-8"))
    writer.write(output_json_bytes)


@contextmanager
def models_dump_stream(debug: bool, writer: StreamWriter):
    try:
        yield
    finally:
        writer.write("-1\n".encode("utf-8"))


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
