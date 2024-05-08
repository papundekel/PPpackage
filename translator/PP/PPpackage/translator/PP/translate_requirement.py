from collections.abc import Iterable, Mapping

from .schemes import Parameters


def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[dict[str, str]]],
    requirement: str,
) -> Iterable[str]:
    yield "TODO"
