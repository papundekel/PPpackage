from collections.abc import Iterable
from pathlib import Path

from .schemes import PathTranslation


def translate(path_translations: Iterable[PathTranslation], container_path: Path):
    for path_translation in path_translations:
        if container_path.absolute().is_relative_to(path_translation.container):
            return (
                path_translation.containerizer
                / container_path.absolute().relative_to(
                    path_translation.container.absolute()
                )
            ).absolute()

    raise ValueError(f"Path {container_path} is not in any of the translations")
