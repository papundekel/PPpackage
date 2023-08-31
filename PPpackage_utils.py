import sys
import json
import os
import asyncio
import typer
import inspect
import functools


class AsyncTyper(typer.Typer):
    @staticmethod
    def maybe_run_async(decorator, f):
        if inspect.iscoroutinefunction(f):

            @functools.wraps(f)
            def runner(*args, **kwargs):
                return asyncio.run(f(*args, **kwargs))

            decorator(runner)
        else:
            decorator(f)
        return f

    def callback(self, *args, **kwargs):
        decorator = super().callback(*args, **kwargs)
        return functools.partial(self.maybe_run_async, decorator)

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)
        return functools.partial(self.maybe_run_async, decorator)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def ensure_dir_exists(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


class MyException(Exception):
    pass


class STDERRException(Exception):
    def __init__(self, message, stderr):
        super().__init__(message)
        self.stderr = stderr

    def __str__(self):
        return f"{super().__str__()}\n{self.stderr}"


def subprocess_communicate(process, error_message, input=None):
    stdout, stderr = process.communicate(input)

    if process.returncode != 0:
        if stderr is not None:
            raise STDERRException(error_message, stderr)
        else:
            raise MyException(error_message)

    return stdout


async def asubprocess_communicate(
    process: asyncio.subprocess.Process, error_message, input=None
):
    stdout, stderr = await process.communicate(input)

    if process.returncode != 0:
        if stderr is not None:
            raise STDERRException(error_message, stderr.decode("ascii"))
        else:
            raise MyException(error_message)

    return stdout


def check_dict_format(input, keys_required, keys_permitted_unequired, error_message):
    if type(input) is not dict:
        raise MyException(error_message)

    keys = input.keys()

    keys_permitted = keys_required | keys_permitted_unequired

    are_present_required = keys_required <= keys
    are_present_only_permitted = keys <= keys_permitted

    if not are_present_required or not are_present_only_permitted:
        raise MyException(error_message)


def check_lockfile_simple(lockfile_input):
    if type(lockfile_input) is not dict:
        raise MyException("Invalid lockfile format: not a dict.")

    for package, version in lockfile_input.items():
        if type(package) is not str:
            raise MyException(
                f"Invalid lockfile package format: `{package}` not a string."
            )
        if type(version) is not str:
            raise MyException(
                f"Invalid lockfile version format: `{version}` not a string."
            )


def parse_lockfile_simple(input):
    check_lockfile_simple(input)

    lockfile = input

    return lockfile


def parse_generators(input):
    if type(input) is not list:
        raise MyException("Invalid generators format: not a list.")

    for generator_input in input:
        if type(generator_input) is not str:
            raise MyException("Invalid generator format: not a string.")

    generators = set(input)

    if len(generators) != len(input):
        raise MyException("Invalid generators format: multiple identical values.")

    return generators


def parse_resolve_input(requirements_parser, options_parser, input):
    check_dict_format(
        input, {"requirements", "options"}, set(), "Invalid resolve input format."
    )

    requirements = requirements_parser(input["requirements"])
    options = options_parser(input["options"])

    return requirements, options


def parse_fetch_input(lockfile_parser, options_parser, input):
    check_dict_format(
        input,
        {"lockfile", "options", "generators"},
        set(),
        "Invalid fetch input format.",
    )

    lockfile = lockfile_parser(input["lockfile"])
    options = options_parser(input["options"])
    generators = parse_generators(input["generators"])

    return lockfile, options, generators


def check_products_simple(products_input):
    if type(products_input) is not dict:
        raise MyException("Invalid products format")

    for package, version_info in products_input.items():
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


class Product:
    def __init__(self, package, version, product_id):
        self.package = package
        self.version = version
        self.product_id = product_id


def parse_products_simple(products_input):
    check_products_simple(products_input)

    return [
        Product(
            package=package,
            version=version_info["version"],
            product_id=version_info["product_id"],
        )
        for package, version_info in products_input.items()
    ]


app = AsyncTyper()


def init(
    submanagers_handler,
    resolver,
    fetcher,
    installer,
    requirements_parser,
    options_parser,
    lockfile_parser,
    products_parser,
):
    @app.command()
    async def submanagers():
        submanagers = await submanagers_handler()

        json.dump(submanagers, sys.stdout)

    @app.command()
    async def resolve(cache_path: str):
        input = json.load(sys.stdin)

        requirements, options = parse_resolve_input(
            requirements_parser, options_parser, input
        )

        lockfiles = await resolver(cache_path, requirements, options)

        json.dump(lockfiles, sys.stdout)

    @app.command()
    async def fetch(cache_path: str, generators_path: str):
        input = json.load(sys.stdin)

        lockfile, options, generators = parse_fetch_input(
            lockfile_parser, options_parser, input
        )

        products = await fetcher(
            cache_path, lockfile, options, generators, generators_path
        )

        json.dump(products, sys.stdout)

    @app.command()
    async def install(cache_path: str, destination_path: str):
        input = json.load(sys.stdin)

        ensure_dir_exists(destination_path)

        products = products_parser(input)

        await installer(cache_path, products, destination_path)


def run(manager_id):
    try:
        app()
    except* MyException as eg:
        for e in eg.exceptions:
            print(f"{manager_id}: {e}", file=sys.stderr)
        sys.exit(1)
