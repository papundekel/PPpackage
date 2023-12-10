from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from pathlib import Path


def get_cache_paths(cache_path: Path) -> tuple[Path, Path]:
    database_path = cache_path / "arch" / "db"
    cache_path = cache_path / "arch" / "cache"
    return database_path, cache_path


@dataclass(frozen=True)
class RunnerConnection:
    reader: StreamReader
    writer: StreamWriter
    workdir_path: Path
