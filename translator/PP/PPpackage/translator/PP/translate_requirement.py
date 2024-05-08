from collections.abc import AsyncIterable, Iterable, Mapping

from pysat.formula import Formula, Or

from .schemes import Parameters


def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[dict[str, str]]],
    requirement: str,
) -> Iterable[str]:
    yield "TODO"
