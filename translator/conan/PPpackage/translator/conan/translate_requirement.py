from collections.abc import Iterable, Mapping

from conans.model.version import Version
from conans.model.version_range import VersionRange
from pysat.formula import Atom, Formula, Or

from .schemes import Parameters, Requirement


async def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[str]],
    requirement: Requirement,
) -> Formula:
    versions = data.get(f"conan-{requirement.package}", [])

    if requirement.version.startswith("[") and requirement.version.endswith("]"):
        version_range = VersionRange(requirement.version[1:-1])

        return Or(
            *(
                Atom(f"conan-{requirement.package}/{version}")
                for version in versions
                if version_range.contains(Version(version.rsplit("#", 1)[0]), False)
            )
        )
    elif requirement.version.find("#") == -1:
        return Or(
            *(
                Atom(f"conan-{requirement.package}/{version}")
                for version in versions
                if version.startswith(f"{requirement.version}#")
            )
        )
    else:
        return Atom(f"conan-{requirement.package}/{requirement.version}")
