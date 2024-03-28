from inspect import isclass
from json import loads as json_loads
from typing import Any, TypeVar

from pydantic import BaseModel, RootModel

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
