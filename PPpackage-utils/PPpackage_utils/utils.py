from asyncio import Queue as BaseQueue
from asyncio import (
    StreamReader,
    StreamReaderProtocol,
    StreamWriter,
    create_subprocess_exec,
    get_event_loop,
)
from asyncio.streams import FlowControlMixin
from asyncio.subprocess import DEVNULL, PIPE, Process
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterator,
    MutableMapping,
)
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from enum import Enum
from enum import auto as enum_auto
from enum import unique as enum_unique
from io import BytesIO
from os import environ, getgid, getuid, kill, mkfifo
from pathlib import Path
from shutil import rmtree
from signal import SIGTERM
from sys import stderr, stdin, stdout
from tarfile import DIRTYPE, TarFile, TarInfo
from tempfile import TemporaryDirectory as BaseTemporaryDirectory
from typing import IO, Any, Optional, Protocol, TypeVar

from frozendict import frozendict


class MyException(Exception):
    pass


class STDERRException(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        super().__init__(message)
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{super().__str__()}\n{self.stderr}"


Lockfile = frozendict[str, str]


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@contextmanager
def TemporaryDirectory(dir=None):
    with BaseTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


async def asubprocess_wait(process: Process, exception: Exception) -> None:
    return_code = await process.wait()

    if return_code != 0:
        raise exception


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


async def get_fakeroot_info(debug: bool):
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
async def fakeroot(debug: bool) -> AsyncIterator[MutableMapping[str, str]]:
    pid = None
    try:
        fakeroot_info_task = get_fakeroot_info(debug)

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


@enum_unique
class ImageType(Enum):
    TAG = enum_auto()
    DOCKERFILE = enum_auto()


@enum_unique
class RunnerRequestType(Enum):
    INIT = enum_auto()
    COMMAND = enum_auto()
    RUN = enum_auto()
    END = enum_auto()


async def get_standard_streams():
    loop = get_event_loop()
    reader = StreamReader()
    protocol = StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(FlowControlMixin, stdout)
    writer = StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


def debug_redirect_stderr(debug: bool):
    return DEVNULL if not debug else None


def debug_redirect_stdout(debug: bool):
    return DEVNULL if not debug else stderr


@contextmanager
def TarFileInMemoryRead(data: memoryview) -> Iterator[TarFile]:
    with BytesIO(data) as io:
        with TarFile(fileobj=io, mode="r") as tar:
            yield tar


class TarFileWithBytes(Protocol):
    data: memoryview

    def addfile(self, tarinfo: TarInfo, fileobj: IO[bytes] | None):
        ...

    def add(self, name: str, arcname: str):
        ...

    def getmembers(self) -> list[TarInfo]:
        ...


def tar_append(from_data: memoryview, to_tar: TarFileWithBytes) -> None:
    with TarFileInMemoryRead(from_data) as from_tar:
        from_members = from_tar.getmembers()
        to_members = to_tar.getmembers()

        append_members = (
            from_member
            for from_member in from_members
            if all(from_member.name != to_member.name for to_member in to_members)
        )

        for member in append_members:
            fileobj = (
                from_tar.extractfile(member)
                if not member.islnk() and not member.issym()
                else None
            )

            to_tar.addfile(member, fileobj)


@contextmanager
def TarFileInMemoryWrite() -> Generator[TarFileWithBytes, Any, None]:
    io = BytesIO()

    with TarFile(fileobj=io, mode="w") as tar:
        yield tar  # type: ignore

    setattr(tar, "data", io.getbuffer())


@contextmanager
def TarFileInMemoryAppend(data: memoryview) -> Generator[TarFileWithBytes, Any, None]:
    io = BytesIO(data)

    with TarFile(fileobj=io, mode="a") as tar:
        yield tar  # type: ignore

    setattr(tar, "data", io.getbuffer())


async def discard_async_iterable(async_iterable: AsyncIterable[Any]) -> None:
    async for _ in async_iterable:
        pass


def create_tar_directory(tar, path: Path):
    info = TarInfo(name=str(path))
    info.mode = 0o755
    info.type = DIRTYPE

    tar.addfile(info)


@contextmanager
def create_tar_file(tar, path: Path):
    with BytesIO() as io:
        yield io

        io.seek(0)

        info = TarInfo(name=str(path))
        info.size = len(io.getbuffer())

        tar.addfile(info, io)


def create_empty_tar() -> memoryview:
    with TarFileInMemoryWrite() as tar:
        pass

    return tar.data


def wipe_directory_onerror(_, __, excinfo):
    _, exc, _ = excinfo

    if not isinstance(exc, FileNotFoundError):
        raise exc


def wipe_directory(directory: Path) -> None:
    for path in directory.iterdir():
        if path.is_symlink():
            path.unlink()
        else:
            rmtree(path, onerror=wipe_directory_onerror)


class SubmanagerCommand(Enum):
    UPDATE_DATABASE = enum_auto()
    RESOLVE = enum_auto()
    FETCH = enum_auto()
    GENERATE = enum_auto()
    INSTALL_PATCH = enum_auto()
    INSTALL_POST = enum_auto()
    INSTALL_PUT = enum_auto()
    INSTALL_GET = enum_auto()
    INSTALL_DELETE = enum_auto()
    END = enum_auto()


@dataclass(frozen=True)
class RunnerInfo:
    socket_path: Path
    workdirs_path: Path


def tar_extract(tar_bytes: memoryview, destination_path: Path):
    wipe_directory(destination_path)

    with TarFileInMemoryRead(tar_bytes) as tar:
        tar.extractall(
            destination_path,
            filter=lambda info, path: info.replace(uid=getuid(), gid=getgid()),
        )


def tar_archive(source_path: Path) -> memoryview:
    with TarFileInMemoryWrite() as tar:
        tar.add(str(source_path), "")

    return tar.data


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


class SubmanagerCommandFailure(Exception):
    pass


class _InstallationsImpl:
    def __init__(self, max: int):
        self.mapping = dict[int, memoryview]()
        self.max = max
        self.i = 0

    def _find_new_i(self, i: int) -> int:
        new_i = i + 1

        while new_i in self.mapping:
            if new_i >= self.max:
                new_i = 0

            new_i += 1

        return new_i

    def add(self, installation: memoryview) -> str:
        i = self.i

        self.mapping[i] = installation

        self.i = self._find_new_i(i)

        return str(i)

    def put(self, id: str, installation: memoryview) -> None:
        i = int(id)

        self.mapping[i] = installation

    def get(self, id: str) -> memoryview:
        i = int(id)

        return self.mapping[i]

    def remove(self, id: str) -> None:
        i = int(id)

        del self.mapping[i]


class Installations(_InstallationsImpl):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add(self, installation: memoryview) -> str:
        try:
            return super().add(installation)
        except:
            raise SubmanagerCommandFailure

    def put(self, id: str, installation: memoryview) -> None:
        try:
            super().put(id, installation)
        except:
            raise SubmanagerCommandFailure

    def get(self, id: str) -> memoryview:
        try:
            return super().get(id)
        except:
            raise SubmanagerCommandFailure

    def remove(self, id: str) -> None:
        try:
            super().remove(id)
        except:
            raise SubmanagerCommandFailure
