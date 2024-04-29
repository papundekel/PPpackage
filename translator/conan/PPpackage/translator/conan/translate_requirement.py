from collections.abc import Iterable, Mapping

from conans.model.version import Version
from conans.model.version_range import VersionRange
from pysat.formula import Atom, Formula, Or

from .schemes import Parameters, Requirement


async def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[dict[str, str]]],
    requirement: Requirement,
) -> Formula:
    symbols = data.get(f"conan-{requirement.package}", [])

    if requirement.version.startswith("[") and requirement.version.endswith("]"):
        version_range = VersionRange(requirement.version[1:-1])

        return Or(
            *(
                Atom(
                    f"conan-{requirement.package}/{symbol['version']}#{symbol['revision']}"
                )
                for symbol in symbols
                if version_range.contains(Version(symbol["version"]), False)
            )
        )
    elif requirement.version.find("#") == -1:
        return Or(
            *(
                Atom(
                    f"conan-{requirement.package}/{symbol['version']}#{symbol['revision']}"
                )
                for symbol in symbols
                if symbol["version"] == requirement.version
            )
        )
    else:
        return Atom(f"conan-{requirement.package}/{requirement.version}")
