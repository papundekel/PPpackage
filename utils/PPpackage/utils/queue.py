from asyncio.queues import Queue as BaseQueue
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from typing import TypeVar

T = TypeVar("T")

Queue = BaseQueue[T | None]


async def queue_iterate(queue: Queue[T]) -> AsyncIterable[T]:
    while True:
        value = await queue.get()

        if value is None:
            break

        yield value


@asynccontextmanager
async def queue_put_loop(queue: Queue[T]):
    try:
        yield
    finally:
        await queue.put(None)
