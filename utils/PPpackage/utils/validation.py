from inspect import isclass
from json import dumps as json_dumps
from json import loads as json_loads
from os import environ
from pathlib import Path
from string import Template
from typing import Any, TypeVar

from pydantic import AfterValidator, BaseModel, RootModel

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


def load_from_string(Model: type[ModelType], input_json_string: str) -> ModelType:
    input_json = json_loads(input_json_string)

    return load_object(Model, input_json)


def load_from_bytes(Model: type[ModelType], input_json_bytes: memoryview) -> ModelType:
    input_json_string = str(input_json_bytes, encoding="utf-8")

    return load_from_string(Model, input_json_string)


def wrap(output: BaseModel | Any) -> BaseModel:
    return output if isinstance(output, BaseModel) else RootModel(output)


def save_object(output: BaseModel | Any) -> Any:
    output_wrapped = wrap(output)

    return output_wrapped.model_dump()


def save_to_string(output: BaseModel | Any) -> str:
    output_wrapped = wrap(output)

    output_json = output_wrapped.model_dump()

    output_json_string = json_dumps(output_json, sort_keys=True, separators=(",", ":"))

    return output_json_string


T = TypeVar("T")


def substitute_environment_variables(value_or_path: str | Path):
    value = value_or_path if isinstance(value_or_path, str) else str(value_or_path)

    substituted_value = Template(value).safe_substitute(environ)

    return (
        substituted_value if isinstance(value_or_path, str) else Path(substituted_value)
    )


WithVariables = AfterValidator(substitute_environment_variables)
