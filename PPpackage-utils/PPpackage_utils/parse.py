from collections.abc import Mapping, Set
from sys import stderr
from typing import Annotated, Any, Generic, Sequence, TypedDict, TypeVar

from PPpackage_utils.utils import MyException, frozendict
from pydantic import BaseModel, BeforeValidator, RootModel, ValidationError
from pydantic.dataclasses import dataclass


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
