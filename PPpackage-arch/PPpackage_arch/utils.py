from dataclasses import dataclass
from pathlib import Path

from httpx import AsyncClient as HTTPClient


def get_cache_paths(cache_path: Path) -> tuple[Path, Path]:
    database_path = cache_path / Path("db")
    cache_path = cache_path / Path("cache")
    return database_path, cache_path


@dataclass(frozen=True)
class State:
    runner_client: HTTPClient
