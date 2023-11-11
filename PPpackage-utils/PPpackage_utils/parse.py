import dataclasses
from collections.abc import Hashable, Iterable, Mapping, Set
from dataclasses import is_dataclass
from json import JSONEncoder
from json import dump as json_dump_base
from json import dumps as json_dumps_base
from json import load as json_load_base
from json import loads as json_loads_base
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


def json_hook(d: dict[str, Any]) -> Mapping[str, Any]:
    return frozendict(d)


def json_loads(input: str) -> Any:
    return json_loads_base(input, object_hook=json_hook)


def json_load(fp) -> Any:
    return json_load_base(fp, object_hook=json_hook)


class CustomEncoder(JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, bool):
            return obj
        elif obj is None:
            return obj
        elif isinstance(obj, int):
            return obj
        elif isinstance(obj, float):
            return obj
        elif is_dataclass(obj):
            return self.default(dataclasses.asdict(obj))
        elif isinstance(obj, Mapping):
            return {self.default(k): self.default(v) for k, v in obj.items()}
        elif isinstance(obj, Iterable):
            return [self.default(o) for o in obj]

        super().default(obj)


def json_dump(obj, fp, **kwargs) -> None:
    json_dump_base(obj, fp, cls=CustomEncoder, **kwargs)


def json_dumps(obj, **kwargs) -> str:
    return json_dumps_base(obj, cls=CustomEncoder, **kwargs)


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
