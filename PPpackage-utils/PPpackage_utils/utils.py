from asyncio import create_subprocess_exec
from asyncio.subprocess import Process
from collections.abc import Callable, Mapping, MutableMapping, Set
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
from sys import stderr
from tempfile import TemporaryDirectory as TempfileTemporaryDirectory
from typing import Any, AsyncIterator, Optional

from frozendict import frozendict


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@contextmanager
def TemporaryDirectory(dir=None):
    with TempfileTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


class MyException(Exception):
    pass


class STDERRException(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        super().__init__(message)
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{super().__str__()}\n{self.stderr}"


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


def json_check_format(
    debug: bool,
    input: Any,
    keys_required: Set[str],
    keys_permitted_unequired: Set[str],
    error_message: str,
) -> Mapping[str, Any]:
    if type(input) is not frozendict:
        raise MyException(error_message)

    keys = input.keys()

    keys_permitted = keys_required | keys_permitted_unequired

    are_present_required = keys_required <= keys
    are_present_only_permitted = keys <= keys_permitted

    if not are_present_required or not are_present_only_permitted:
        if debug:
            print(input, file=stderr)

        raise MyException(error_message)

    return input


def parse_generators(input: Any) -> Set[str]:
    if type(input) is not list:
        raise MyException("Invalid generators format: not a list.")

    for generator_input in input:
        if type(generator_input) is not str:
            raise MyException("Invalid generator format: not a string.")

    generators = set(input)

    if len(generators) != len(input):
        raise MyException("Invalid generators format: multiple identical values.")

    return generators


def parse_resolve_input(
    debug: bool,
    requirements_parser: Callable[[bool, Any], Set[Any]],
    options_parser: Callable[[bool, Any], Any],
    input: Any,
) -> tuple[Set[Any], Any]:
    input_checked = json_check_format(
        debug,
        input,
        {"requirements", "options"},
        set(),
        "Invalid resolve input format.",
    )

    requirements = requirements_parser(debug, input_checked["requirements"])
    options = options_parser(debug, input_checked["options"])

    return requirements, options


def parse_fetch_input(
    debug: bool,
    lockfile_parser: Callable[[bool, Any], Mapping[str, str]],
    options_parser: Callable[[bool, Any], Any],
    input: Any,
) -> tuple[Mapping[str, str], Any, Set[str]]:
    input_checked = json_check_format(
        debug,
        input,
        {"lockfile", "options", "generators"},
        set(),
        "Invalid fetch input format.",
    )

    lockfile = lockfile_parser(debug, input_checked["lockfile"])
    options = options_parser(debug, input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return lockfile, options, generators


def check_products_simple(debug: bool, input: Any) -> Mapping[str, Mapping[str, str]]:
    if type(input) is not frozendict:
        raise MyException("Invalid products format")

    for package, version_info in input.items():
        if type(package) is not str:
            raise MyException("Invalid products format")

        json_check_format(
            debug,
            version_info,
            {"version", "product_id"},
            set(),
            "Invalid products format",
        )

        version = version_info["version"]
        product_id = version_info["product_id"]

        if type(version) is not str:
            raise MyException("Invalid products format")

        if type(product_id) is not str:
            raise MyException("Invalid products format")

    return input


class Product:
    def __init__(self, package: str, version: str, product_id: str):
        self.package = package
        self.version = version
        self.product_id = product_id


def parse_products(debug: bool, input: Any) -> Set[Product]:
    input_checked = check_products_simple(debug, input)

    return {
        Product(
            package=package,
            version=version_info["version"],
            product_id=version_info["product_id"],
        )
        for package, version_info in input_checked.items()
    }


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


class SetEncoder(JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        return JSONEncoder.default(self, obj)


def json_dump(obj, fp, **kwargs) -> None:
    json_dump_base(obj, fp, cls=SetEncoder, **kwargs)


def json_dumps(obj, **kwargs) -> str:
    return json_dumps_base(obj, cls=SetEncoder, **kwargs)
