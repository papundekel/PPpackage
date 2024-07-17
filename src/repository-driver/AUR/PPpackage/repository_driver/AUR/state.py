from dataclasses import dataclass
from pathlib import Path

from aiosqlite import Connection


@dataclass(frozen=True)
class State:
    database_path: Path
    connection: Connection
