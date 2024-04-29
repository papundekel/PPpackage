from collections.abc import Callable, Iterable, Mapping
from itertools import chain
from operator import eq, ge, gt, le, lt
from sys import stderr

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
    version_left: str | None,
    comparison: Callable[[int, int], bool],
    version_right: str,
) -> bool:
    if version_left is None:
        return False

    cmp = alpm_vercmp(version_left, version_right)

    return comparison(cmp, 0)


def create_atoms(
    package: str,
    prefix: str,
    symbols: Iterable[dict[str, str]],
    requirement_expression: tuple[Callable[[int, int], bool], str] | None,
) -> Iterable[Formula]:
    for symbol in symbols:
        if requirement_expression is None or version_compare(
            symbol.get("version"),
            requirement_expression[0],
            requirement_expression[1],
        ):
            yield Atom(
                f"pacman-{prefix}-{package}-{symbol['version']}"
                if "version" in symbol
                else f"pacman-{prefix}-{package}"
            )


async def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[dict[str, str]]],
    requirement: str,
) -> Formula:
    package, requirement_expression = parse_requirement(requirement)

    real_symbols = data.get(f"pacman-real-{package}", [])
    virtual_symbols = data.get(f"pacman-virtual-{package}", [])

    return Or(
        *(
            chain(
                create_atoms(package, "real", real_symbols, requirement_expression),
                create_atoms(
                    package, "virtual", virtual_symbols, requirement_expression
                ),
            )
        )
    )
