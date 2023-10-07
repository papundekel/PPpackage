from collections.abc import Iterable, Mapping, Set
from typing import Any
from typing import cast as typing_cast

from PPpackage_utils.utils import MyException, check_dict_format

from .utils import Options, Requirement


def check_requirements(input: Any) -> Iterable[Mapping[str, str]]:
    if type(input) is not list:
        raise MyException("Invalid requirements format.")

    for requirement_input in input:
        check_dict_format(
            requirement_input,
            {"package", "version"},
            set(),
            "Invalid requirement format.",
        )

        if type(requirement_input["package"]) is not str:
            raise MyException("Invalid requirement format.")

        if type(requirement_input["version"]) is not str:
            raise MyException("Invalid requirement format.")

    return input


def parse_requirements(input: Any) -> Set[Requirement]:
    input_checked = check_requirements(input)

    return {
        Requirement(requirement_input["package"], requirement_input["version"])
        for requirement_input in input_checked
    }


def check_options(input: Any) -> Options:
    input_checked = typing_cast(
        Options,
        check_dict_format(
            input, set(), {"settings", "options"}, "Invalid input format."
        ),
    )

    for category_input, assignments_input in input_checked.items():
        if type(assignments_input) is not dict:
            raise MyException(
                f"Invalid input format. options[{category_input}] not a dict."
            )

        for value in assignments_input.values():
            if type(value) is not str:
                raise MyException(f"Invalid input format. `{value}` not a string.")

    return input_checked


def parse_options(input: Any) -> Options:
    input_checked = check_options(input)

    options = input_checked

    return options
