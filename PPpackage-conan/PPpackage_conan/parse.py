from typing import Any

from pydantic import BaseModel
from pydantic.dataclasses import dataclass


class FetchProductInfo(BaseModel):
    version: str
    cpp_info: Any


@dataclass(frozen=True)
class Requirement:
    package: str
    version: str
