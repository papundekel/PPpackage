from collections.abc import Iterable, Mapping

from pysat.formula import And, Atom, Formula, Or

from .schemes import Parameters, Requirement


def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: Requirement,
) -> Formula:
    related_packages = grouped_packages.get(f"conan-{requirement.package}")

    if related_packages is None:
        return And(Atom(None), ~Atom(None))

    return Or(*(Atom(package) for package in related_packages))
