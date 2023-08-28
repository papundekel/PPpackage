import sys
import json
import os


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


def parse_lockfile_simple(lockfile_input):
    check_lockfile_simple(lockfile_input)
    return lockfile_input


def parse_generators(generators_input):
    if type(generators_input) is not list:
        raise MyException("Invalid generators format: not a list.")

    for generator_input in generators_input:
        if type(generator_input) is not str:
            raise MyException("Invalid generator format: not a string.")

    return generators_input


def parse_lockfile_generators(lockfile_parser, lockfile_generators_input):
    check_dict_format(
        lockfile_generators_input,
        {"lockfile", "generators"},
        set(),
        "Invalid lockfile-generators format",
    )

    lockfile = lockfile_parser(lockfile_generators_input["lockfile"])
    generators = parse_generators(lockfile_generators_input["generators"])

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


def execute(
    manager_id,
    resolver,
    fetcher,
    installer,
    requirements_parser,
    lockfile_parser,
    products_parser,
    additional_commands,
):
    try:
        command = sys.argv[1] if len(sys.argv) >= 2 else None

        required_commands = {"resolve", "fetch", "install"}

        if command not in required_commands | additional_commands.keys():
            raise MyException(f"Unknown command `{command}`.")

        cache_path = parse_cl_argument(2, "Missing cache path argument.")

        if command in required_commands:
            input = json.load(sys.stdin)

            if command == "resolve":
                requirements = requirements_parser(input)

                lockfile_versions = resolver(cache_path, requirements)

                json.dump(lockfile_versions, sys.stdout)

            elif command == "fetch":
                generators_path = parse_cl_argument(
                    3, "Missing generators path argument."
                )

                lockfile, generators = parse_lockfile_generators(lockfile_parser, input)

                products = fetcher(cache_path, lockfile, generators, generators_path)

                json.dump(products, sys.stdout)

            elif command == "install":
                destination_path = parse_cl_argument(
                    3, "Missing destination path argument."
                )

                ensure_dir_exists(destination_path)

                products = products_parser(input)

                installer(cache_path, products, destination_path)

        else:
            command_handler = additional_commands.get(command)

            if command_handler is None:
                raise MyException("Internal error.")

            command_handler(cache_path, *sys.argv[3:])

    except MyException as e:
        print(f"{manager_id}: {e}", file=sys.stderr)
        sys.exit(1)
