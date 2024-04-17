from pathlib import Path
from typing import Annotated

from pydantic.dataclasses import dataclass as pydantic_dataclass

from PPpackage.utils.validation import WithVariables


@pydantic_dataclass(frozen=True)
class PathTranslation:
    containerizer: Annotated[Path, WithVariables]
    container: Annotated[Path, WithVariables]
