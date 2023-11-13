from collections.abc import Hashable, Mapping, Set
from sys import stderr
from typing import Annotated, Any, Generic, Sequence, TypeVar, get_args

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

ModelType = TypeVar("ModelType", bound=BaseModel)


def model_validate_obj(Model: type[ModelType], obj: Any) -> ModelType:
    try:
        input = Model.model_validate(obj)

        return input
    except ValidationError as e:
        raise MyException(f"Invalid model format:\n{e}.")


def model_validate(
    debug: bool, Model: type[ModelType], input_json_bytes: bytes
) -> ModelType:
    input_json_string = input_json_bytes.decode("utf-8")

    if debug:
        print(
            f"DEBUG model_validate {Model}:\n{input_json_string}",
            file=stderr,
            flush=True,
        )

    try:
        input = Model.model_validate_json(input_json_string)

        return input
    except ValidationError as e:
        raise MyException(f"Invalid model format:\n{e}\n{input_json_string}.")


def model_dump(debug: bool, output: BaseModel) -> bytes:
    output_json_string = output.model_dump_json(indent=4 if debug else None)

    if debug:
        print(f"DEBUG model_dump:\n{output_json_string}", file=stderr)

    output_json_bytes = output_json_string.encode("utf-8")

    return output_json_bytes


FrozenDictPydantic = Annotated[
    frozendict[Key, Value], FrozenDictAnnotation[Key, Value]()
]

Requirement = TypeVar("Requirement")


class ResolveInput(BaseModel, Generic[Requirement]):
    options: Mapping[str, Any] | None
    requirements_list: Sequence[Set[Requirement]]


@dataclass(frozen=True)
class Product:
    name: str
    version: str
    product_id: str


class GenerateInput(BaseModel):
    options: Mapping[str, Any] | None
    generators: Set[str]
    products: Set[Product]


class FetchOutputValue(BaseModel):
    product_id: str
    product_info: Any


FetchOutput = RootModel[Mapping[str, FetchOutputValue]]


@dataclass(frozen=True)
class PackageWithDependencies:
    name: str
    version: str
    dependencies: FrozenDictPydantic[str, Set[str]]


class FetchInput(BaseModel):
    options: Mapping[str, Any] | None
    packages: Set[PackageWithDependencies]
    product_infos: Mapping[str, Mapping[str, Any]]


InstallInput = RootModel[Set[Product]]


@dataclass(frozen=True)
class ResolutionGraphNodeValue:
    version: str
    dependencies: Set[str]
    requirements: FrozenDictPydantic[str, frozenset[Hashable]]


@dataclass(frozen=True)
class ResolutionGraph:
    roots: tuple[Set[str], ...]
    graph: FrozenDictPydantic[str, ResolutionGraphNodeValue]
