from asyncio import (
    StreamReader,
    StreamReaderProtocol,
    StreamWriter,
    create_subprocess_exec,
    get_event_loop,
)
from asyncio.streams import FlowControlMixin
from asyncio.subprocess import DEVNULL, PIPE, Process
from collections.abc import AsyncIterator, Generator, MutableMapping
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from enum import auto as enum_auto
from enum import unique as enum_unique
from io import BytesIO
from os import environ, kill, mkfifo
from pathlib import Path
from signal import SIGTERM
from sys import stderr, stdin, stdout
from tarfile import TarFile, TarInfo
from tempfile import TemporaryDirectory as TempfileTemporaryDirectory
from typing import IO, Any, Optional, Protocol

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
    with TempfileTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


async def asubprocess_wait(process: Process, error_message: str) -> None:
    return_code = await process.wait()

    if return_code != 0:
        raise MyException(error_message)


async def asubprocess_communicate(
    process: Process,
    error_message: str,
    input: Optional[bytes] = None,
) -> bytes:
    stdout, stderr = await process.communicate(input)

    if process.returncode != 0:
        if stderr is not None:
            raise STDERRException(error_message, stderr.decode("ascii"))
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
            line.strip() for line in fakeroot_stdout.decode("ascii").splitlines()
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

        key, pid_string = faked_stdout.decode("ascii").strip().split(":")

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
def communicate_from_sub(pipe_from_sub_path):
    with open(pipe_from_sub_path, "w") as pipe_from_sub:
        try:
            yield pipe_from_sub
        finally:
            pipe_from_sub.write("END\n")


@contextmanager
def TemporaryPipe(dir=None):
    with TemporaryDirectory(dir) as dir_path:
        pipe_path = dir_path / "pipe"

        mkfifo(pipe_path)

        yield pipe_path


def noop(*args, **kwargs):
    pass


async def anoop(*args, **kwargs):
    pass


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


MACHINE_ID_RELATIVE_PATH = Path("etc") / "machine-id"


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id


@contextmanager
def TarFileInMemoryRead(data: bytes):
    with BytesIO(data) as io:
        with TarFile(fileobj=io, mode="r") as tar:
            yield tar


class TarFileWithBytes(Protocol):
    data: bytes

    def addfile(self, tarinfo: TarInfo, fileobj: IO[bytes] | None):
        ...

    def add(self, name: str, arcname: str):
        ...


@contextmanager
def TarFileInMemoryWrite() -> Generator[TarFileWithBytes, Any, None]:
    with BytesIO() as io:
        with TarFile(fileobj=io, mode="w") as tar:
            yield tar  # type: ignore

        setattr(tar, "data", io.getvalue())
