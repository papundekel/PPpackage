from collections.abc import Mapping, Set
from sys import stderr
from typing import Any

from PPpackage_utils.parse import parse_lockfile
from PPpackage_utils.utils import (
    MyException,
    Resolution,
    frozendict,
    json_check_format,
    parse_generators,
)


def check_requirements(debug: bool, requirements_json: Any) -> None:
    if type(requirements_json) is not list:
        if debug:
            print(
                f"Got {requirements_json}.",
                file=stderr,
            )
        raise MyException(
            "Invalid meta requirements format. Manager requirements should be a list."
        )


def parse_requirements(debug: bool, requirements_json: Any) -> Set[Any]:
    check_requirements(debug, requirements_json)

    requirements = frozenset(requirements_json)

    return requirements


def check_meta_requirements(debug: bool, meta_requirements_json: Any) -> None:
    if type(meta_requirements_json) is not frozendict:
        raise MyException("Invalid requirements format. Should be a dictionary.")


def parse_meta_requirements(
    debug: bool, meta_requirements_json: Any
) -> Mapping[str, Set[Any]]:
    check_meta_requirements(debug, meta_requirements_json)

    meta_requirements = frozendict(
        {
            manager: parse_requirements(debug, requirements)
            for manager, requirements in meta_requirements_json.items()
        }
    )

    return meta_requirements


def check_meta_options(meta_options_json: Any) -> None:
    if type(meta_options_json) is not frozendict:
        raise MyException("Invalid meta options format.")

    for options_json in meta_options_json.values():
        # TODO: rethink
        if type(options_json) is not frozendict:
            raise MyException("Invalid options format.")


def parse_meta_options(meta_options_json: Any) -> Mapping[str, Mapping[str, Any]]:
    check_meta_options(meta_options_json)

    meta_options = meta_options_json

    return meta_options


def parse_input(
    debug: bool,
    input_json: Any,
) -> tuple[Mapping[str, Set[Any]], Mapping[str, Any], Set[str]]:
    json_check_format(
        debug,
        input_json,
        {"requirements", "options", "generators"},
        set(),
        "Invalid input format.",
    )

    meta_requirements = parse_meta_requirements(debug, input_json["requirements"])
    meta_options = parse_meta_options(input_json["options"])
    generators = parse_generators(input_json["generators"])

    return meta_requirements, meta_options, generators


def check_resolution(
    debug: bool,
    resolution_json: Any,
) -> None:
    json_check_format(
        debug,
        resolution_json,
        {"lockfile", "requirements"},
        set(),
        "Invalid resolution format.",
    )


def check_resolutions(
    debug: bool,
    resolutions_json: Any,
) -> None:
    if type(resolutions_json) is not list:
        raise MyException("Invalid resolutions format.")


def parse_resolution(
    debug: bool,
    resolution_json: Any,
) -> Resolution:
    check_resolution(debug, resolution_json)

    lockfile = parse_lockfile(debug, resolution_json["lockfile"])
    requirements = parse_meta_requirements(debug, resolution_json["requirements"])

    return Resolution(lockfile, requirements)


def parse_resolutions(
    debug: bool,
    resolutions_json: Any,
) -> Set[Resolution]:
    check_resolutions(debug, resolutions_json)

    resolutions = frozenset(
        parse_resolution(debug, resolution_json) for resolution_json in resolutions_json
    )

    return resolutions
