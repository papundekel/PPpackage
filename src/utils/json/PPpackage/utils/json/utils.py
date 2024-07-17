from typing import Any

from pydantic import BaseModel, RootModel


def wrap_instance(output: Any) -> BaseModel:
    return output if isinstance(output, BaseModel) else RootModel(output)
