from inspect import isclass
from pathlib import Path
from typing import IO, Any

from pydantic import BaseModel, RootModel


def _unwrap_instance(output: Any) -> Any:
    return output.root if isinstance(output, RootModel) else output


def _wrap_model[T](Model: type[T]) -> type[BaseModel]:
    return (
        Model if isclass(Model) and issubclass(Model, BaseModel) else RootModel[Model]
    )


def validate_python[T](Model: type[T], input_python: Any) -> T:
    ModelWrapped = _wrap_model(Model)

    input_wrapped = ModelWrapped.model_validate(input_python)

    input = _unwrap_instance(input_wrapped)

    return input


def validate_json[T](Model: type[T], input_json: str | bytes) -> T:
    ModelWrapped = _wrap_model(Model)

    input_wrapped = ModelWrapped.model_validate_json(input_json)

    input = _unwrap_instance(input_wrapped)

    return input


def validate_json_io[T](Model: type[T], input_io: IO[bytes]) -> T:
    input_json = input_io.read()

    input = validate_json(Model, input_json)

    return input


def validate_json_io_path[T](Model: type[T], input_path: Path) -> T:
    with input_path.open("rb") as input_io:
        input = validate_json_io(Model, input_io)

    return input
