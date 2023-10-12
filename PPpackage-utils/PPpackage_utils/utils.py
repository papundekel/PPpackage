from asyncio import create_subprocess_exec
from asyncio.subprocess import Process
from collections import namedtuple
from collections.abc import AsyncIterator, Iterable, Mapping, MutableMapping
from contextlib import asynccontextmanager, contextmanager
from json import JSONEncoder
from json import dump as json_dump_base
from json import dumps as json_dumps_base
from json import load as json_load_base
from json import loads as json_loads_base
from os import environ, kill, mkfifo
from pathlib import Path
from signal import SIGTERM
from subprocess import DEVNULL, PIPE
from tempfile import TemporaryDirectory as TempfileTemporaryDirectory
from typing import Any, Optional

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


class Product:
    def __init__(self, package: str, version: str, product_id: str):
        self.package = package
        self.version = version
        self.product_id = product_id


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@contextmanager
def TemporaryDirectory(dir=None):
    with TempfileTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


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
            stderr=None,
        )

        fakeroot_stdout = await asubprocess_communicate(
            await process_creation, "Error in `fakeroot`."
        )

        ld_library_path, ld_preload = tuple(
            [line.strip() for line in fakeroot_stdout.decode("ascii").splitlines()]
        )

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
            stderr=None,
        )

        faked_stdout = await asubprocess_communicate(
            await process_creation, "Error in `faked`."
        )

        key, pid_string = tuple(faked_stdout.decode("ascii").strip().split(":"))

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


def json_hook(d: dict[str, Any]) -> Mapping[str, Any]:
    return frozendict(d)


def json_loads(input: str) -> Any:
    return json_loads_base(input, object_hook=json_hook)


def json_load(fp) -> Any:
    return json_load_base(fp, object_hook=json_hook)


def isinstance_namedtuple(obj) -> bool:
    return (
        isinstance(obj, tuple) and hasattr(obj, "_asdict") and hasattr(obj, "_fields")
    )


class CustomEncoder(JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, bool):
            return obj
        elif obj is None:
            return obj
        elif isinstance(obj, int):
            return obj
        elif isinstance(obj, float):
            return obj
        elif isinstance_namedtuple(obj):
            return self.default(obj._asdict())
        elif isinstance(obj, Mapping):
            return {self.default(k): self.default(v) for k, v in obj.items()}
        elif isinstance(obj, Iterable):
            return [self.default(o) for o in obj]

        super().default(obj)


def json_dump(obj, fp, **kwargs) -> None:
    json_dump_base(obj, fp, cls=CustomEncoder, **kwargs)


def json_dumps(obj, **kwargs) -> str:
    return json_dumps_base(obj, cls=CustomEncoder, **kwargs)


Resolution = namedtuple("Resolution", ["lockfile", "requirements"])
