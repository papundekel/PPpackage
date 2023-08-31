import sys
import json
import asyncio
import typer
import inspect
import functools
from pathlib import Path
from collections.abc import Mapping, Set, Callable, Iterable, Awaitable
from typing import Any, Optional, TypedDict


def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


class AsyncTyper(typer.Typer):
    @staticmethod
    def maybe_run_async(decorator: Callable[[Any], Any], f: Any) -> Any:
        if inspect.iscoroutinefunction(f):

            @functools.wraps(f)
            def runner(*args: Any, **kwargs: Any) -> Any:
                return asyncio.run(f(*args, **kwargs))

            decorator(runner)
        else:
            decorator(f)
        return f

    def callback(self, *args: Any, **kwargs: Any) -> Any:
        decorator = super().callback(*args, **kwargs)
        return functools.partial(self.maybe_run_async, decorator)

    def command(self, *args: Any, **kwargs: Any) -> Any:
        decorator = super().command(*args, **kwargs)
        return functools.partial(self.maybe_run_async, decorator)


class SetEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class MyException(Exception):
    pass


class STDERRException(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        super().__init__(message)
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{super().__str__()}\n{self.stderr}"


async def asubprocess_communicate(
    process: asyncio.subprocess.Process,
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


def check_dict_format(
    input: Any,
    keys_required: Set[str],
    keys_permitted_unequired: Set[str],
    error_message: str,
) -> Mapping[str, Any]:
    if type(input) is not dict:
        raise MyException(error_message)

    keys = input.keys()

    keys_permitted = keys_required | keys_permitted_unequired

    are_present_required = keys_required <= keys
    are_present_only_permitted = keys <= keys_permitted

    if not are_present_required or not are_present_only_permitted:
        raise MyException(error_message)

    return input


def check_lockfile_simple(input: Any) -> Mapping[str, str]:
    if type(input) is not dict:
        raise MyException("Invalid lockfile format: not a dict.")

    for package_input, version_input in input.items():
        if type(package_input) is not str:
            raise MyException(
                f"Invalid lockfile package format: `{package_input}` not a string."
            )

        if type(version_input) is not str:
            raise MyException(
                f"Invalid lockfile version format: `{version_input}` not a string."
            )

    return input


def parse_lockfile_simple(input: Any) -> Mapping[str, str]:
    input_checked = check_lockfile_simple(input)

    lockfile = input_checked

    return lockfile


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
    requirements_parser: Callable[[Any], Iterable[Any]],
    options_parser: Callable[[Any], Any],
    input: Any,
) -> tuple[Iterable[Any], Any]:
    input_checked = check_dict_format(
        input, {"requirements", "options"}, set(), "Invalid resolve input format."
    )

    requirements = requirements_parser(input_checked["requirements"])
    options = options_parser(input_checked["options"])

    return requirements, options


def parse_fetch_input(
    lockfile_parser: Callable[[Any], Mapping[str, str]],
    options_parser: Callable[[Any], Any],
    input: Any,
) -> tuple[Mapping[str, str], Any, Set[str]]:
    input_checked = check_dict_format(
        input,
        {"lockfile", "options", "generators"},
        set(),
        "Invalid fetch input format.",
    )

    lockfile = lockfile_parser(input_checked["lockfile"])
    options = options_parser(input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return lockfile, options, generators


def check_products_simple(input: Any) -> Mapping[str, Mapping[str, str]]:
    if type(input) is not dict:
        raise MyException("Invalid products format")

    for package, version_info in input.items():
        if type(package) is not str:
            raise MyException("Invalid products format")

        check_dict_format(
            version_info, {"version", "product_id"}, set(), "Invalid products format"
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


def parse_products_simple(input: Any) -> Set[Product]:
    input_checked = check_products_simple(input)

    return {
        Product(
            package=package,
            version=version_info["version"],
            product_id=version_info["product_id"],
        )
        for package, version_info in input_checked.items()
    }


_debug = False


app = AsyncTyper()


@app.callback()
def callback(debug: bool = False) -> None:
    global _debug
    _debug = debug


def init(
    submanagers_handler: Callable[[], Awaitable[Iterable[str]]],
    resolver: Callable[
        [Path, Iterable[Any], Any], Awaitable[Iterable[Mapping[str, str]]]
    ],
    fetcher: Callable[
        [Path, Mapping[str, str], Any, Set[str], Path],
        Awaitable[Mapping[str, str]],
    ],
    installer: Callable[[Path, Set[Product], Path], Awaitable[None]],
    requirements_parser: Callable[[Any], Iterable[Any]],
    options_parser: Callable[[Any], Any],
    lockfile_parser: Callable[[Any], Mapping[str, str]],
    products_parser: Callable[[Any], Set[Product]],
) -> None:
    @app.command()
    async def submanagers() -> None:
        submanagers = await submanagers_handler()

        json.dump(submanagers, sys.stdout)

    @app.command()
    async def resolve(cache_path: Path) -> None:
        input = json.load(sys.stdin)

        requirements, options = parse_resolve_input(
            requirements_parser, options_parser, input
        )

        lockfiles = await resolver(cache_path, requirements, options)

        indent = 4 if _debug else None

        json.dump(lockfiles, sys.stdout, indent=indent)

    @app.command()
    async def fetch(cache_path: Path, generators_path: Path) -> None:
        input = json.load(sys.stdin)

        lockfile, options, generators = parse_fetch_input(
            lockfile_parser, options_parser, input
        )

        product_ids = await fetcher(
            cache_path, lockfile, options, generators, generators_path
        )

        indent = 4 if _debug else None

        json.dump(product_ids, sys.stdout, indent=indent)

    @app.command()
    async def install(cache_path: Path, destination_path: Path) -> None:
        input = json.load(sys.stdin)

        ensure_dir_exists(destination_path)

        products = products_parser(input)

        await installer(cache_path, products, destination_path)


def run(manager_id: str) -> None:
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"{manager_id}: {e}", file=sys.stderr)
        sys.exit(1)
