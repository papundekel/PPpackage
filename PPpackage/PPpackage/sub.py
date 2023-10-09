from collections.abc import Iterable, Mapping, Set
from pathlib import Path
from typing import Any

from PPpackage_utils.utils import Resolution, frozendict


async def update_database(debug: bool, cache_path: Path) -> None:
    pass


async def resolve(
    debug: bool,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> Set[Resolution]:
    lockfile = frozendict({name: "1.0.0" for name in set(requirements)})
    new_requirements = frozendict({"arch": frozenset(["iana-etc"])})

    return frozenset([Resolution(lockfile, new_requirements)])


async def fetch(
    debug: bool,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    product_ids = {name: "id" for name in versions.keys()}

    return product_ids


async def install(
    debug: bool,
    cache_path: Path,
    destination_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    products_path = destination_path / "PP"

    products_path.mkdir(exist_ok=True)

    for name, version in versions.items():
        product_id = product_ids[name]

        product_path = products_path / name
        product_path.write_text(f"{version} {product_id}")
