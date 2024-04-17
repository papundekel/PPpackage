from collections.abc import Set
from pathlib import Path
from typing import Annotated

from pydantic import AnyUrl, BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.container_utils.schemes import PathTranslation
from PPpackage.utils.validation import WithVariables


@pydantic_dataclass(frozen=True)
class ContainerizerConfig:
    url: Annotated[AnyUrl, WithVariables]
    path_translations: Set[PathTranslation] = frozenset(
        [PathTranslation(container=Path("/"), containerizer=Path("/"))]
    )


class Parameters(BaseModel):
    containerizer: ContainerizerConfig
