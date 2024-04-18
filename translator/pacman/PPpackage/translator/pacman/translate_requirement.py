from collections.abc import Iterable, Mapping

from pysat.formula import Atom, Formula, Or

from .schemes import Parameters


def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]


async def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    package = strip_version(requirement)

    related_packages = grouped_packages.get(f"pacman-{package}")

    if related_packages is None:
        return Atom(f"pacman-{package}")

    return Or(*(Atom(package) for package in related_packages))
