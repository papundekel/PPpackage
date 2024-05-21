from collections.abc import Set
from pathlib import Path
from typing import Annotated

from pydantic import AnyUrl
from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.json.validator import WithVariables


@pydantic_dataclass(frozen=True)
class PathTranslation:
    containerizer: Annotated[Path, WithVariables]
    container: Annotated[Path, WithVariables]


@pydantic_dataclass(frozen=True)
class ContainerizerConfig:
    url: Annotated[AnyUrl, WithVariables]
    path_translations: Set[PathTranslation] = frozenset(
        [PathTranslation(container=Path("/"), containerizer=Path("/"))]
    )
