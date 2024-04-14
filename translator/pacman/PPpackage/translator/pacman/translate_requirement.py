from collections.abc import Iterable, Mapping

from pysat.formula import Atom, Formula, Or

from .schemes import Parameters


async def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    related_packages = grouped_packages.get(f"pacman-{requirement}")

    if related_packages is None:
        return Atom(f"pacman-{requirement}")

    return Or(*(Atom(package) for package in related_packages))
