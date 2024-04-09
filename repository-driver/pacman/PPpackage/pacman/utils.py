from pathlib import Path


def get_cache_paths(cache_path: Path) -> tuple[Path, Path]:
    database_path = cache_path / Path("db")
    cache_path = cache_path / Path("cache")
    return database_path, cache_path
