from collections.abc import AsyncIterable, Callable, Iterable, Mapping
from operator import eq, ge, gt, le, lt

from pyalpm import vercmp as alpm_vercmp

from .schemes import ExcludeRequirement, Parameters


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
    symbols: Iterable[dict[str, str]],
    version_expression: tuple[Callable[[int, int], bool], str] | None,
    exclude: str | None,
) -> Iterable[str]:
    for symbol in symbols:
        provider = symbol.get("provider")
        version = symbol.get("version")

        package_suffix = provider if provider is not None else f"{name}-{version}"

        if package_suffix == exclude:
            continue

        if version_expression is None or version_compare(
            version,
            version_expression[0],
            version_expression[1],
        ):
            yield f"pacman-{package_suffix}"


def translate_requirement(
    parameters: Parameters,
    data: Mapping[str, Iterable[dict[str, str]]],
    requirement: str | ExcludeRequirement,
) -> Iterable[str]:
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
