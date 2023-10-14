from collections.abc import Set
from pathlib import Path

from PPpackage_utils.utils import Resolution


async def resolve(
    cache_path: Path, requirements: Set[str], options: None
) -> Set[Resolution]:
    return frozenset()
