from collections.abc import Iterable, Mapping

from pysat.formula import PYSAT_FALSE, Atom, Formula, Or

from .schemes import Parameters


def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    related_packages = grouped_packages.get(f"PP-{requirement}")

    if related_packages is None:
        return PYSAT_FALSE

    return Or(*(Atom(package) for package in related_packages))
