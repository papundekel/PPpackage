from dataclasses import dataclass
from pathlib import Path

from aiorwlock import RWLock
from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from fasteners import InterProcessReaderWriterLock
from pydantic import AnyUrl


@dataclass(frozen=True)
class State:
    database_path: Path
    url: AnyUrl
    verify_ssl: bool
    coroutine_lock: RWLock
    file_lock: InterProcessReaderWriterLock
    api: ConanAPI
    app: ConanApp
    aux_home_paths: list[Path]
