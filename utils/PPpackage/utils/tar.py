from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from os import getgid, getuid
from pathlib import Path
from tarfile import DIRTYPE, TarFile, TarInfo
from typing import IO, Protocol

from .utils import wipe_directory


@contextmanager
def TarFileInMemoryRead(data: memoryview) -> Iterator[TarFile]:
    with BytesIO(data) as io:
        with TarFile(fileobj=io, mode="r") as tar:
            yield tar


class TarFileWithBytes(Protocol):
    data: memoryview

    def addfile(self, tarinfo: TarInfo, fileobj: IO[bytes] | None): ...

    def add(self, name: str, arcname: str): ...

    def getmembers(self) -> list[TarInfo]: ...


def append(from_data: memoryview, to_tar: TarFileWithBytes) -> None:
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
def TarFileInMemoryWrite() -> Iterator[TarFileWithBytes]:
    io = BytesIO()

    with TarFile(fileobj=io, mode="w") as tar:
        yield tar  # type: ignore

    setattr(tar, "data", io.getbuffer())


@contextmanager
def TarFileInMemoryAppend(data: memoryview) -> Iterator[TarFileWithBytes]:
    io = BytesIO(data)

    with TarFile(fileobj=io, mode="a") as tar:
        yield tar  # type: ignore

    setattr(tar, "data", io.getbuffer())


def create_directory(tar, path: Path):
    info = TarInfo(name=str(path))
    info.mode = 0o755
    info.type = DIRTYPE

    tar.addfile(info)


@contextmanager
def create_file(tar, path: Path):
    with BytesIO() as io:
        yield io

        io.seek(0)

        info = TarInfo(name=str(path))
        info.size = len(io.getbuffer())

        tar.addfile(info, io)


def create_empty() -> memoryview:
    with TarFileInMemoryWrite() as tar:
        pass

    return tar.data


def extract(tar_bytes: memoryview, destination_path: Path):
    wipe_directory(destination_path)

    with TarFileInMemoryRead(tar_bytes) as tar:
        tar.extractall(
            destination_path,
            filter=lambda info, path: info.replace(uid=getuid(), gid=getgid()),
        )


def archive(source_path: Path) -> memoryview:
    with TarFileInMemoryWrite() as tar:
        tar.add(str(source_path), "")

    return tar.data
