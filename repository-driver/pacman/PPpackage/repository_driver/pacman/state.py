from dataclasses import dataclass
from pathlib import Path

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock
from httpx import Client as HTTPClient
from pyalpm import DB, Handle


@dataclass(frozen=True)
class State:
    database_path: Path
    repository: str
    coroutine_lock: RWLock
    file_lock: InterProcessReaderWriterLock
    handle: Handle
    cache_directory_path: Path
    database: DB
    http_client: HTTPClient
