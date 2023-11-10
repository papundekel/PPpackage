from collections.abc import Callable, Mapping, Set
from sys import stderr
from typing import Any, Sequence, TypedDict
from typing import cast as type_cast

from PPpackage_utils.utils import Lockfile, MyException, Product, frozendict, json_dumps
from pydantic import BaseModel, ValidationError


def json_check_format(
    debug: bool,
    input_json: Any,
    keys_required: Set[str],
    keys_permitted_unequired: Set[str],
    error_message: str,
) -> Mapping[str, Any]:
    if type(input_json) is not frozendict:
        raise MyException(error_message)

    keys = input_json.keys()

    keys_permitted = keys_required | keys_permitted_unequired

    are_present_required = keys_required <= keys
    are_present_only_permitted = keys <= keys_permitted

    if not are_present_required or not are_present_only_permitted:
        if debug:
            print(f"json_check_format: {input_json}", file=stderr)

        raise MyException(
            f"{error_message} Must be a JSON object with keys {keys_required} required"
            f"and {keys_permitted_unequired} optional."
        )

    return input_json


def check_lockfile(debug: bool, lockfile_json: Any) -> Lockfile:
    if type(lockfile_json) is not frozendict:
        raise MyException("Invalid lockfile format: not a dict.")

    for version_json in lockfile_json.values():
        if type(version_json) is not str:
            raise MyException(
                f"Invalid lockfile version format: `{version_json}` not a string."
            )

    return lockfile_json


def parse_lockfile(debug: bool, lockfile_json: Any) -> Lockfile:
    lockfile_checked = check_lockfile(debug, lockfile_json)

    return lockfile_checked


def check_generators(debug: bool, generators_json: Any) -> Sequence[str]:
    if type(generators_json) is not list:
        raise MyException("Invalid generators format. Must be a JSON array.")

    for generator_json in generators_json:
        if type(generator_json) is not str:
            raise MyException("Invalid generator format. Must be a string.")

    return generators_json


def parse_generators(generators_json: Any) -> Set[str]:
    generators_checked = check_generators(False, generators_json)

    generators = set(generators_checked)

    if len(generators) != len(generators_checked):
        raise MyException("Invalid generators format. Generators must be unique.")

    return generators


class VersionInfo(TypedDict):
    version: str
    product_id: str


def check_products(debug: bool, products_json: Any) -> Mapping[str, VersionInfo]:
    if type(products_json) is not frozendict:
        raise MyException("Invalid products format. Must be a JSON object.")

    for version_info_json in products_json.values():
        version_info_checked = json_check_format(
            debug,
            version_info_json,
            {"version", "product_id"},
            set(),
            "Invalid products verson info format.",
        )

        version_json = version_info_checked["version"]
        product_id_json = version_info_checked["product_id"]

        if type(version_json) is not str:
            raise MyException("Invalid products version format. Must be a string.")

        if type(product_id_json) is not str:
            raise MyException("Invalid products product id format. Must be a string.")

    return products_json


def parse_products(debug: bool, products_json: Any) -> Set[Product]:
    products_checked = check_products(debug, products_json)

    return {
        Product(
            package=package_checked,
            version=version_info_checked["version"],
            product_id=version_info_checked["product_id"],
        )
        for package_checked, version_info_checked in products_checked.items()
    }


class ResolveInput(TypedDict):
    requirements: Any
    options: Any


def check_resolve_input(debug: bool, input_json: Any) -> ResolveInput:
    return type_cast(
        ResolveInput,
        json_check_format(
            debug,
            input_json,
            {"requirements", "options"},
            set(),
            "Invalid resolve input format.",
        ),
    )


def parse_resolve_input(
    debug: bool,
    requirements_parser: Callable[[bool, Any], Set[Any]],
    options_parser: Callable[[bool, Any], Any],
    input_json: Any,
) -> tuple[Sequence[Set[Any]], Any]:
    input_checked = check_resolve_input(debug, input_json)

    requirements_list_json = input_checked["requirements"]

    for requirements_json in requirements_list_json:
        if type(requirements_json) is not list:
            raise MyException("Invalid requirements format. Must be a JSON array.")

    requirements_list = [
        requirements_parser(debug, requirements_json)
        for requirements_json in requirements_list_json
    ]
    options = options_parser(debug, input_checked["options"])

    return requirements_list, options


class FetchInput(TypedDict):
    lockfile: Any
    options: Any


def check_fetch_input(debug: bool, input_json: Any) -> FetchInput:
    return type_cast(
        FetchInput,
        json_check_format(
            debug,
            input_json,
            {"lockfile", "options"},
            set(),
            "Invalid fetch input format.",
        ),
    )


def parse_fetch_input(
    debug: bool,
    lockfile_parser: Callable[[bool, Any], Mapping[str, str]],
    options_parser: Callable[[bool, Any], Any],
    input_json: Any,
) -> tuple[Mapping[str, str], Any]:
    input_checked = check_fetch_input(debug, input_json)

    lockfile = lockfile_parser(debug, input_checked["lockfile"])
    options = options_parser(debug, input_checked["options"])

    return lockfile, options


class GenerateInputPackagesValue(BaseModel):
    version: str
    product_id: str


class GenerateInput(BaseModel):
    generators: Set[str]
    packages: Mapping[str, GenerateInputPackagesValue]
    options: Mapping[str, Any] | None


def parse_generate_input(
    debug: bool,
    input_json: Any,
) -> GenerateInput:
    try:
        return GenerateInput.model_validate(input_json)
    except ValidationError:
        raise MyException(
            f"Invalid generate input format: {json_dumps(input_json, indent=4)}."
        )
