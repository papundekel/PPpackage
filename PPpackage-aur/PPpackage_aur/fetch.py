from collections.abc import Mapping, Set
from pathlib import Path
from typing import Any


async def fetch(
    cache_path: Path,
    lockfile: Mapping[str, str],
    options: Any,
    generators: Set[str],
    generators_path: Path,
) -> Mapping[str, str]:
    return {}
