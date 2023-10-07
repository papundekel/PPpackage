from collections.abc import Iterable, Mapping, Set
from typing import Any

from PPpackage_utils.utils import MyException, check_dict_format, parse_generators


def check_requirements(input: Any) -> Mapping[str, Iterable[Any]]:
    if type(input) is not dict:
        raise MyException("Invalid requirements format.")

    for manager, requirements in input.items():
        if type(manager) is not str:
            raise MyException("Invalid requirements format.")

        if type(requirements) is not list:
            raise MyException("Invalid requirements format.")

    return input


def parse_requirements(input: Any) -> Mapping[str, Set[Any]]:
    input_checked = check_requirements(input)

    requirements = input_checked

    return {
        manager: set(requirements) for manager, requirements in requirements.items()
    }


def check_options(input: Any) -> Mapping[str, Mapping[str, Any]]:
    if type(input) is not dict:
        raise MyException("Invalid options format.")

    for manager_input, options_input in input.items():
        if type(manager_input) is not str:
            raise MyException("Invalid options format.")

        # TODO: rethink
        if type(options_input) is not dict:
            raise MyException("Invalid options format.")

    return input


def parse_options(input: Any) -> Mapping[str, Mapping[str, Any]]:
    input_checked = check_options(input)

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

    requirements = parse_requirements(input_checked["requirements"])
    options = parse_options(input_checked["options"])
    generators = parse_generators(input_checked["generators"])

    return requirements, options, generators
