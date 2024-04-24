from collections.abc import Iterable, Mapping

from pysat.formula import Formula, Or

from .schemes import Parameters, Requirement


async def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: Requirement,
) -> Formula:
    return Or()
