from inspect import isclass
from json import dumps as json_dumps
from os import environ
from pathlib import Path
from string import Template
from typing import IO, Any

from pydantic import AfterValidator, BaseModel, RootModel


def wrap_instance(output: Any) -> BaseModel:
    return output if isinstance(output, BaseModel) else RootModel(output)


def unwrap_instance(output: Any) -> Any:
    return output.root if isinstance(output, RootModel) else output


def wrap_model[T](Model: type[T]):
    return (
        Model if isclass(Model) and issubclass(Model, BaseModel) else RootModel[Model]
    )


def validate_python[T](Model: type[T], input_python: Any) -> T:
    ModelWrapped = wrap_model(Model)

    input_wrapped = ModelWrapped.model_validate(input_python)

    input = unwrap_instance(input_wrapped)

    return input


def validate_json[T](Model: type[T], input_json: str | bytes) -> T:
    ModelWrapped = wrap_model(Model)

    input_wrapped = ModelWrapped.model_validate_json(input_json)

    input = unwrap_instance(input_wrapped)

    return input


def validate_json_io[T](Model: type[T], input_io: IO[bytes]) -> T:
    input_json = input_io.read()

    input = validate_json(Model, input_json)

    return input


def validate_json_io_path[T](Model: type[T], input_path: Path) -> T:
    with input_path.open("rb") as input_io:
        input = validate_json_io(Model, input_io)

    return input


def dump_python(output: Any) -> Any:
    output_wrapped = wrap_instance(output)

    output_python = output_wrapped.model_dump()

    return output_python


def dump_json(output: Any) -> str:
    output_python = dump_python(output)

    output_json = json_dumps(output_python, sort_keys=True, separators=(",", ":"))

    return output_json


def substitute_environment_variables(value: Any):
    value_string = str(value)

    substituted_value = Template(value_string).safe_substitute(environ)

    return type(value)(substituted_value)


WithVariables = AfterValidator(substitute_environment_variables)
