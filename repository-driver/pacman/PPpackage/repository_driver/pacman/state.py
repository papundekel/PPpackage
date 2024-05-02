from dataclasses import dataclass
from pathlib import Path

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock
from pyalpm import Handle


@dataclass(frozen=True)
class State:
    coroutine_lock: RWLock
    file_lock: InterProcessReaderWriterLock
    handle: Handle
    cache_directory_path: Path
