from collections.abc import Iterable, Mapping

from conans.model.version import Version
from conans.model.version_range import VersionRange

from .schemes import Parameters, Requirement


def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[dict[str, str]]],
    requirement: Requirement,
) -> Iterable[str]:
    symbols = data.get(f"conan-{requirement.package}", [])

    if requirement.version.startswith("[") and requirement.version.endswith("]"):
        version_range = VersionRange(requirement.version[1:-1])

        for symbol in symbols:
            if version_range.contains(Version(symbol["version"]), False):
                yield f"conan-{requirement.package}/{symbol['version']}#{symbol['revision']}"

    elif requirement.version.find("#") == -1:
        for symbol in symbols:
            if symbol["version"] == requirement.version:
                yield f"conan-{requirement.package}/{symbol['version']}#{symbol['revision']}"

    else:
        yield f"conan-{requirement.package}/{requirement.version}"
