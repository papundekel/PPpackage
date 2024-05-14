from collections.abc import Callable, Iterable, Mapping
from operator import eq, ge, gt, le, lt

from pyalpm import vercmp as alpm_vercmp

from PPpackage.translator.interface.schemes import Data

from .schemes import ExcludeRequirement, NoProvideRequirement, Parameters
from .utils import process_symbol


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
    name: str,
    symbols: Iterable[Mapping[str, str]],
    version_expression: tuple[Callable[[int, int], bool], str] | None,
    exclude: str | None,
) -> Iterable[str]:
    for symbol in symbols:
        package_suffix, version = process_symbol(name, symbol)

        if package_suffix == exclude:
            continue

        if version_expression is None or version_compare(
            version,
            version_expression[0],
            version_expression[1],
        ):
            yield f"pacman-{package_suffix}"


def handle_no_provide(data: Data, requirement: NoProvideRequirement) -> str | None:
    symbols = data.get(f"pacman-{requirement.package}", [])

    for symbol in symbols:
        if "provider" not in symbol:
            return f"pacman-{requirement.package}-{symbol['version']}"

    return None


def translate_requirement(
    parameters: Parameters,
    data: Data,
    requirement: str | ExcludeRequirement | NoProvideRequirement,
) -> Iterable[str]:
    if isinstance(requirement, NoProvideRequirement):
        literal = handle_no_provide(data, requirement)

        if literal is not None:
            yield literal

        return

    requirement_name = (
        requirement if isinstance(requirement, str) else requirement.package
    )

    exclude = (
        requirement.exclude if isinstance(requirement, ExcludeRequirement) else None
    )

    name, version_expression = parse_requirement(requirement_name)

    symbols = data.get(f"pacman-{name}", [])

    for literal in create_atoms(name, symbols, version_expression, exclude):
        yield literal
