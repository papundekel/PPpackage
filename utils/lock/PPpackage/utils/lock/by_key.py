from asyncio import Lock
from collections.abc import MutableMapping
from contextlib import asynccontextmanager


@asynccontextmanager
async def lock_by_key[T](locks: MutableMapping[T, Lock], key: T):
    lock = locks.setdefault(key, Lock())

    async with lock:
        yield
