from collections.abc import AsyncIterable, Callable

from asyncstdlib.itertools import chain as async_chain


class Result[T]:
    def __init__(self):
        self.value = None

    def set(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        if self.value is None:
            raise ValueError("Result not set")

        return self.value


async def get_async_iterable_result[
    R, T
](f: Callable[[Result[R]], AsyncIterable[T]]) -> tuple[R, AsyncIterable[T]]:
    result = Result[R]()

    i = aiter(f(result))

    try:
        first = await anext(i)
    except StopAsyncIteration:
        return result.get(), async_chain()
    else:
        return result.get(), async_chain([first], i)
