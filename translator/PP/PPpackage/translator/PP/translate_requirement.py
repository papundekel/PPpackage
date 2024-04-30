from collections.abc import Iterable, Mapping

from pysat.formula import Formula, Or

from .schemes import Parameters


async def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[dict[str, str]]],
    requirement: str,
) -> Formula:
    return Or()
