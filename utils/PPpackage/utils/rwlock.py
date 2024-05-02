from contextlib import asynccontextmanager

from aiorwlock import RWLock
from fasteners import InterProcessReaderWriterLock


@asynccontextmanager
async def read(coroutine_lock: RWLock, file_lock: InterProcessReaderWriterLock):
    async with coroutine_lock.reader_lock:
        with file_lock.read_lock():
            yield


@asynccontextmanager
async def write(coroutine_lock: RWLock, file_lock: InterProcessReaderWriterLock):
    async with coroutine_lock.writer_lock:
        with file_lock.write_lock():
            yield
