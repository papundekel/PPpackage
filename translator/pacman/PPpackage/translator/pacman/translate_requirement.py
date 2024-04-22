from collections.abc import Iterable, Mapping
from enum import Enum, auto
from sys import stderr

from pyalpm import vercmp as alpm_vercmp
from pysat.formula import Atom, Formula, Or

from .schemes import Parameters


class Comparison(Enum):
    EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    ANY = auto()


def parse_requirement(requirement: str) -> tuple[str, Comparison, str]:
    tokens = requirement.rsplit(">=", 1)
    if len(tokens) == 2:
        return tokens[0], Comparison.GREATER_EQUAL, tokens[1]

    tokens = requirement.rsplit("<=", 1)
    if len(tokens) == 2:
        return tokens[0], Comparison.LESS_EQUAL, tokens[1]

    tokens = requirement.rsplit(">", 1)
    if len(tokens) == 2:
        return tokens[0], Comparison.GREATER, tokens[1]

    tokens = requirement.rsplit("<", 1)
    if len(tokens) == 2:
        return tokens[0], Comparison.LESS, tokens[1]

    tokens = requirement.rsplit("=", 1)
    if len(tokens) == 2:
        return tokens[0], Comparison.EQUAL, tokens[1]

    return requirement, Comparison.ANY, ""


def parse_package_version(package_version: str) -> str:
    tokens = package_version.rsplit("-", 3)

    if len(tokens) != 4:
        raise Exception(f"Invalid package version: {package_version}")

    return tokens[1]


def version_less(version_left: str, version_right: str) -> bool:
    compare_code = alpm_vercmp(version_left, version_right)

    return compare_code < 0


def version_compare(
    version_left: str, comparison: Comparison, version_right: str
) -> bool:
    match comparison:
        case Comparison.EQUAL:
            return version_left == version_right
        case Comparison.GREATER:
            return version_less(version_right, version_left)
        case Comparison.GREATER_EQUAL:
            return not version_less(version_left, version_right)
        case Comparison.LESS:
            return version_less(version_left, version_right)
        case Comparison.LESS_EQUAL:
            return not version_less(version_right, version_left)
        case Comparison.ANY:
            return True


async def translate_requirement(
    parameters: Parameters,
    grouped_packages: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    package, comparison, version = parse_requirement(requirement)

    related_packages = grouped_packages.get(f"pacman-{package}")

    if related_packages is None:
        return Atom(f"pacman-{package}")

    result = Or(
        *(
            Atom(package)
            for package in related_packages
            if version_compare(parse_package_version(package), comparison, version)
        )
    )

    return result
