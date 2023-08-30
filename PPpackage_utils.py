import sys
import json
import os


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


def subprocess_communicate(process, error_message, input):
    stdout, stderr = process.communicate(input)

    if process.returncode != 0:
        if stderr is not None:
            raise STDERRException(error_message, stderr)
        else:
            raise MyException(error_message)

    return stdout


def subprocess_wait(process, error_message):
    return subprocess_communicate(process, error_message, None)


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


def parse_lockfile_generators(lockfile_parser, input):
    check_dict_format(
        input,
        {"lockfile", "generators"},
        set(),
        "Invalid lockfile-generators format.",
    )

    lockfile = lockfile_parser(input["lockfile"])
    generators = parse_generators(input["generators"])

    return lockfile, generators


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


def parse_cl_argument(index, error_message):
    if not len(sys.argv) > index:
        raise MyException(error_message)

    return sys.argv[index]


def submanagers(submanagers_handler):
    submanagers = submanagers_handler()

    json.dump(submanagers, sys.stdout)


def resolve(requirements_parser, resolver):
    cache_path = parse_cl_argument(2, "Missing cache path argument.")

    input = json.load(sys.stdin)

    requirements = requirements_parser(input)

    lockfiles = resolver(cache_path, requirements)

    json.dump(lockfiles, sys.stdout)


def fetch(lockfile_parser, fetcher):
    cache_path = parse_cl_argument(2, "Missing cache path argument.")
    generators_path = parse_cl_argument(3, "Missing generators path argument.")

    input = json.load(sys.stdin)

    lockfile, generators = parse_lockfile_generators(lockfile_parser, input)

    products = fetcher(cache_path, lockfile, generators, generators_path)

    json.dump(products, sys.stdout)


def install(products_parser, installer):
    cache_path = parse_cl_argument(2, "Missing cache path argument.")
    destination_path = parse_cl_argument(3, "Missing destination path argument.")

    input = json.load(sys.stdin)

    ensure_dir_exists(destination_path)

    products = products_parser(input)

    installer(cache_path, products, destination_path)


def execute(
    manager_id,
    submanagers_handler,
    resolver,
    fetcher,
    installer,
    requirements_parser,
    lockfile_parser,
    products_parser,
    additional_commands,
):
    try:
        if not len(sys.argv) > 1:
            raise MyException("Missing command argument.")

        command = sys.argv[1]

        required_commands = {
            "submanagers": lambda: submanagers(submanagers_handler),
            "resolve": lambda: resolve(requirements_parser, resolver),
            "fetch": lambda: fetch(lockfile_parser, fetcher),
            "install": lambda: install(products_parser, installer),
        }

        commands = additional_commands | required_commands

        command_handler = commands.get(command)

        if command_handler is None:
            raise MyException("Unknown command `{command}`")

        command_handler()

    except MyException as e:
        print(f"{manager_id}: {e}", file=sys.stderr)
        sys.exit(1)
