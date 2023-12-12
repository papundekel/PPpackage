from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import Options, ResolutionGraph

from .update_database import update_database
from .utils import get_cache_paths


async def resolve(
    debug: bool,
    data: Any,
    session_data: None,
    cache_path: Path,
    options: Options,
    requirements_list: AsyncIterable[AsyncIterable[str]],
) -> AsyncIterable[ResolutionGraph]:
    database_path, _ = get_cache_paths(cache_path)

    if not database_path.exists():
        await update_database(debug, data, session_data, cache_path)

    yield ResolutionGraph([[]], [])
