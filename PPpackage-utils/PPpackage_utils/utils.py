from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE, Process
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Iterable,
    Mapping,
    MutableMapping,
    Set,
)
from contextlib import asynccontextmanager, contextmanager
from os import environ, kill, mkfifo
from pathlib import Path
from shutil import move
from shutil import rmtree as base_rmtree
from signal import SIGTERM
from tempfile import TemporaryDirectory as BaseTemporaryDirectory
from typing import Any, Optional, TypeVar, overload

from frozendict import frozendict
from pydantic.dataclasses import dataclass as pydantic_dataclass


class MyException(Exception):
    pass


class STDERRException(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        super().__init__(message)
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{super().__str__()}\n{self.stderr}"


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@contextmanager
def TemporaryDirectory(dir=None):
    with BaseTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


async def asubprocess_wait(process: Process, exception: Exception) -> int:
    return_code = await process.wait()

    if return_code != 0:
        raise exception

    return return_code


async def asubprocess_communicate(
    process: Process,
    error_message: str,
    input: Optional[bytes] = None,
) -> bytes:
    stdout, stderr = await process.communicate(input)

    if process.returncode != 0:
        if stderr is not None:
            raise STDERRException(error_message, stderr.decode())
        else:
            raise MyException(error_message)

    return stdout


class FakerootInfo:
    def __init__(self, ld_library_path, ld_preload):
        self.ld_library_path = ld_library_path
        self.ld_preload = ld_preload


_fakeroot_info = None


async def get_fakeroot_info():
    global _fakeroot_info

    if _fakeroot_info is None:
        process_creation = create_subprocess_exec(
            "fakeroot",
            "printenv",
            "LD_LIBRARY_PATH",
            "LD_PRELOAD",
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=DEVNULL,
        )

        fakeroot_stdout = await asubprocess_communicate(
            await process_creation, "Error in `fakeroot`."
        )

        ld_library_path, ld_preload = [
            line.strip() for line in fakeroot_stdout.decode().splitlines()
        ]

        _fakeroot_info = FakerootInfo(ld_library_path, ld_preload)

    return _fakeroot_info


@asynccontextmanager
async def fakeroot() -> AsyncIterator[MutableMapping[str, str]]:
    pid = None
    try:
        fakeroot_info_task = get_fakeroot_info()

        process_creation = create_subprocess_exec(
            "faked",
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=DEVNULL,
        )

        faked_stdout = await asubprocess_communicate(
            await process_creation, "Error in `faked`."
        )

        key, pid_string = faked_stdout.decode().strip().split(":")

        pid = int(pid_string)

        fakeroot_info = await fakeroot_info_task

        environment = environ.copy()

        environment["FAKEROOTKEY"] = key
        environment["LD_LIBRARY_PATH"] = fakeroot_info.ld_library_path
        environment["LD_PRELOAD"] = fakeroot_info.ld_preload

        yield environment
    finally:
        if pid is not None:
            kill(pid, SIGTERM)


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


def _wipe_directory_onerror(_, __, excinfo):
    _, exc, _ = excinfo

    if not isinstance(exc, FileNotFoundError):
        raise exc


def rmtree(path: Path, onerror=None):
    if not path.exists():
        pass
    elif not path.is_symlink() and path.is_dir():
        base_rmtree(path, onerror=onerror)
    else:
        path.unlink()


def wipe_directory(directory: Path) -> None:
    for path in directory.iterdir():
        rmtree(path, onerror=_wipe_directory_onerror)


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


def get_module_path(module) -> Path:
    return Path(module.__file__)


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


@pydantic_dataclass(frozen=True)
class ContainerizerWorkdirInfo:
    containerizer_path: Path
    container_path: Path

    def translate(self, path: Path) -> Path:
        containerizer_path = self.containerizer_path / path.absolute().relative_to(
            self.container_path
        )

        return containerizer_path
