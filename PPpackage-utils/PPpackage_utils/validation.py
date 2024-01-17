from inspect import isclass
from json import loads as json_loads
from sys import stderr
from typing import Any, TypeVar

from pydantic import BaseModel, RootModel

_DEBUG_LOAD = False


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


def load_from_bytes(Model: type[ModelType], input_json_bytes: bytes) -> ModelType:
    input_json_string = input_json_bytes.decode()

    if _DEBUG_LOAD:
        stderr.write(f"load:\n{input_json_string}\n")

    input_json = json_loads(input_json_string)

    return load_object(Model, input_json)
