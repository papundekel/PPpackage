from dataclasses import dataclass

from aiorwlock import RWLock
from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from fasteners import InterProcessReaderWriterLock


@dataclass(frozen=True)
class State:
    coroutine_lock: RWLock
    file_lock: InterProcessReaderWriterLock
    api: ConanAPI
    app: ConanApp
