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


def version_compare(
    version_left: str, comparison: Comparison, version_right: str
) -> bool:
    if comparison == Comparison.ANY:
        return True

    if version_left == "":
        return False

    cmp = alpm_vercmp(version_left, version_right)

    match comparison:
        case Comparison.EQUAL:
            return cmp == 0
        case Comparison.GREATER:
            return cmp > 0
        case Comparison.GREATER_EQUAL:
            return cmp >= 0
        case Comparison.LESS:
            return cmp < 0
        case Comparison.LESS_EQUAL:
            return cmp <= 0


def make_variable(package: str, version: str) -> str:
    if version == "":
        return f"pacman-{package}"

    return f"pacman-{package}-{version}"


async def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    package, comparison, required_version = parse_requirement(requirement)

    versions = data.get(f"pacman-{package}", [])

    result = Or(
        *(
            Atom(make_variable(package, version))
            for version in versions
            if version_compare(version, comparison, required_version)
        )
    )

    if result == Or():
        print(f"Requirement {requirement} is not satisfied", file=stderr)

    return result
