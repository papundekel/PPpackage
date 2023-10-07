from collections.abc import Iterable, Mapping, Set
from typing import Any

from PPpackage_utils.utils import MyException, check_dict_format, parse_generators


def check_meta_requirements(input: Any) -> Mapping[str, Iterable[Any]]:
    if type(input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")

    return input


def parse_meta_requirements(input: Any) -> Mapping[str, Set[Any]]:
    input_checked = check_meta_requirements(input)

    meta_requirements = input_checked

    return {
        manager: set(requirements)
        for manager, requirements in meta_requirements.items()
    }


def check_meta_options(meta_options: Any) -> Mapping[str, Mapping[str, Any]]:
    if type(meta_options) is not dict:
        raise MyException("Invalid meta options format.")

    for manager, options in meta_options.items():
        if type(manager) is not str:
            raise MyException("Invalid options format.")

        # TODO: rethink
        if type(options) is not dict:
            raise MyException("Invalid options format.")

    return meta_options


def parse_meta_options(input: Any) -> Mapping[str, Mapping[str, Any]]:
    input_checked = check_meta_options(input)

    options = input_checked

    return options


def parse_input(
    input: Any,
) -> tuple[Mapping[str, Iterable[Any]], Mapping[str, Any], Set[str]]:
    input_checked = check_dict_format(
        input,
        {"requirements", "options", "generators"},
        set(),
        "Invalid input format.",
    )

    meta_requirements = parse_meta_requirements(input_checked["requirements"])
    meta_options = parse_meta_options(input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return meta_requirements, meta_options, generators
