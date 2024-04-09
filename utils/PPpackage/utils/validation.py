from inspect import isclass
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


def load_from_bytes(Model: type[ModelType], input_json_bytes: memoryview) -> ModelType:
    input_json_string = str(input_json_bytes, encoding="utf-8")

    input_json = json_loads(input_json_string)

    return load_object(Model, input_json)


T = TypeVar("T")


def substitute_environment_variables(value_or_path: str | Path):
    value = value_or_path if isinstance(value_or_path, str) else str(value_or_path)

    substituted_value = Template(value).safe_substitute(environ)

    return (
        substituted_value if isinstance(value_or_path, str) else Path(substituted_value)
    )


WithVariables = AfterValidator(substitute_environment_variables)
