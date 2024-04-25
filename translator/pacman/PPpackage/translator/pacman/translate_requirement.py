from collections.abc import Callable, Iterable, Mapping
from operator import eq, ge, gt, le, lt

from pyalpm import vercmp as alpm_vercmp
from pysat.formula import Atom, Formula, Or

from .schemes import Parameters


def parse_requirement(
    requirement: str,
) -> tuple[str, tuple[Callable[[int, int], bool], str] | None]:
    for token, operator in [
        (">=", ge),
        ("<=", le),
        (">", gt),
        ("<", lt),
        ("=", eq),
    ]:
        match requirement.rsplit(token, 1):
            case package, version:
                return package, (operator, version)

    return requirement, None


def version_compare(
    version_left: str,
    comparison: Callable[[int, int], bool],
    version_right: str,
) -> bool:
    if version_left == "":
        return False

    cmp = alpm_vercmp(version_left, version_right)

    return comparison(cmp, 0)


async def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[str]],
    requirement: str,
) -> Formula:
    package, requirement_expression = parse_requirement(requirement)

    versions = data.get(f"pacman-{package}", [])

    result = Or(
        *(
            Atom(
                f"pacman-{package}-{version}" if version != "" else f"pacman-{package}"
            )
            for version in versions
            if requirement_expression is None
            or version_compare(
                version,
                requirement_expression[0],
                requirement_expression[1],
            )
        )
    )

    return result
