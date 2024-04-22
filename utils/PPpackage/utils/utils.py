from collections.abc import AsyncIterable, Iterable, Mapping, Set
from contextlib import contextmanager
from importlib import import_module
from os import mkfifo
from pathlib import Path
from shutil import move
from tempfile import TemporaryDirectory as BaseTemporaryDirectory
from typing import Any, TypeVar
from typing import cast as type_cast
from typing import overload

from frozendict import frozendict


@contextmanager
def TemporaryDirectory(dir=None):
    with BaseTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


@contextmanager
def TemporaryPipe(dir=None):
    with TemporaryDirectory(dir) as dir_path:
        pipe_path = dir_path / "pipe"

        mkfifo(pipe_path)

        yield pipe_path


async def discard_async_iterable(async_iterable: AsyncIterable[Any]) -> None:
    async for _ in async_iterable:
        pass


T = TypeVar("T")
U = TypeVar("U")


async def make_async_iterable(iterable: Iterable[T]) -> AsyncIterable[T]:
    for item in iterable:
        yield item


def rmtree(path: Path):
    if not path.exists():
        pass
    elif not path.is_symlink() and path.is_dir():
        temp = BaseTemporaryDirectory()
        temp.cleanup()
        temp.name = str(path)
        temp.cleanup()
    else:
        path.unlink()


def wipe_directory(directory: Path) -> None:
    for path in directory.iterdir():
        rmtree(path)


def movetree(source: Path, destination: Path):
    for source_item in source.iterdir():
        destination_item = destination / source_item.name
        rmtree(destination_item)

        if not source_item.is_symlink() and source_item.is_dir():
            destination_item.mkdir()
            movetree(source_item, destination_item)
            source_item.rmdir()
        else:
            move(source_item, destination_item)


@overload
def freeze(x: Mapping[T, U]) -> Mapping[T, U]: ...


@overload
def freeze(x: Set[T]) -> Set[T]: ...


def freeze(x):
    if isinstance(x, Mapping):
        return frozendict({key: freeze(value) for key, value in x.items()})
    elif isinstance(x, Set):
        return frozenset(value for value in x)
    else:
        return x


def load_interface_module(Interface: type[T], package_name: str) -> T:
    return type_cast(T, import_module(f"{package_name}.interface").interface)
