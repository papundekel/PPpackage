from collections.abc import Callable, Mapping, Set
from sys import stderr
from typing import Annotated, Any, Sequence, TypedDict, TypeVar
from typing import cast as type_cast

from PPpackage_utils.utils import MyException, Product, frozendict
from pydantic import BaseModel, BeforeValidator, RootModel, ValidationError


def frozen_validator(value: Any) -> Any:
    if type(value) is dict:
        return frozendict(value)

    return value


FrozenAny = Annotated[Any, BeforeValidator(frozen_validator)]

T = TypeVar("T", bound=BaseModel)


def model_validate_obj(Model: type[T], obj: Any) -> T:
    try:
        input = Model.model_validate(obj)

        return input
    except ValidationError as e:
        raise MyException(f"Invalid model format:\n{e}.")


def model_validate(Model: type[T], input_json_bytes: bytes) -> T:
    input_json_string = input_json_bytes.decode("utf-8")

    try:
        input = Model.model_validate_json(input_json_string)

        return input
    except ValidationError as e:
        raise MyException(f"Invalid model format:\n{e}\n{input_json_string}.")


def model_dump(debug: bool, output: BaseModel) -> bytes:
    output_json_string = output.model_dump_json(indent=4 if debug else None)

    output_json_bytes = output_json_string.encode("utf-8")

    return output_json_bytes


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


def check_generators(debug: bool, generators_json: Any) -> Sequence[str]:
    if type(generators_json) is not list:
        raise MyException("Invalid generators format. Must be a JSON array.")

    for generator_json in generators_json:
        if type(generator_json) is not str:
            raise MyException("Invalid generator format. Must be a string.")

    return generators_json


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


class GenerateInputPackagesValue(BaseModel):
    version: str
    product_id: str


class GenerateInput(BaseModel):
    generators: Set[str]
    packages: Mapping[str, GenerateInputPackagesValue]
    options: Mapping[str, Any] | None


class FetchOutputValue(BaseModel):
    product_id: str
    product_info: Any


FetchOutput = RootModel[Mapping[str, FetchOutputValue]]


class FetchInputPackageValue(BaseModel):
    version: str
    dependencies: Mapping[str, Set[str]]


class FetchInput(BaseModel):
    packages: Mapping[str, FetchInputPackageValue]
    product_infos: Mapping[str, Mapping[str, Any]]
    options: Mapping[str, Any] | None
