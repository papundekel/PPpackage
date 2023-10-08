from collections.abc import Iterable, Mapping, Set
from sys import stderr
from tabnanny import check
from typing import Any

from frozendict import frozendict
from PPpackage_utils.parse import Lockfile, parse_lockfile
from PPpackage_utils.utils import MyException, json_check_format, parse_generators


def check_meta_requirements(debug: bool, meta_requirements_json: Any) -> None:
    if type(meta_requirements_json) is not frozendict:
        raise MyException("Invalid requirements format. Should be a dictionary.")

    for requirements_json in meta_requirements_json.values():
        if type(requirements_json) is not list:
            if debug:
                print(
                    f"Got {requirements_json}.",
                    file=stderr,
                )
            raise MyException(
                "Invalid meta requirements format. Manager requirements should be a list."
            )


def parse_meta_requirements(
    debug: bool, meta_requirements_json: Any
) -> Mapping[str, Set[Any]]:
    check_meta_requirements(debug, meta_requirements_json)

    meta_requirements = {
        manager: set(requirements)
        for manager, requirements in meta_requirements_json.items()
    }

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
        "Invalid input format. Should be a JSON object with keys 'requirements', 'options' and 'generators'.",
    )

    meta_requirements = parse_meta_requirements(debug, input_json["requirements"])
    meta_options = parse_meta_options(input_json["options"])
    generators = parse_generators(input_json["generators"])

    return meta_requirements, meta_options, generators


def check_lockfile_choices(lockfiles_json: Any):
    if type(lockfiles_json) is not list:
        raise MyException("Invalid lockfiles format.")


def parse_lockfile_choices(debug: bool, lockfiles_json: Any):
    check_lockfile_choices(lockfiles_json)

    lockfiles = {
        parse_lockfile(debug, lockfile_json) for lockfile_json in lockfiles_json
    }

    return lockfiles


def parse_resolve_response(
    debug: bool,
    response_json: Any,
) -> tuple[Set[Lockfile], Mapping[str, Set[Any]]]:
    json_check_format(
        debug,
        response_json,
        {"lockfiles", "requirements"},
        set(),
        "Invalid input format. Should be a JSON object with keys 'lockfiles' and 'requirements'.",
    )

    lockfile_choices = parse_lockfile_choices(debug, response_json["lockfiles"])
    new_requirements = parse_meta_requirements(debug, response_json["requirements"])

    return lockfile_choices, new_requirements
