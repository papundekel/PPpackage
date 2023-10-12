from collections.abc import Iterable, Set
from typing import Any, TypedDict
from typing import cast as type_cast

from PPpackage_utils.parse import json_check_format
from PPpackage_utils.utils import MyException, frozendict

from .utils import Options, Requirement


class RequirementJSON(TypedDict):
    package: str
    version: str


def check_requirement(debug: bool, requirement_json: Any) -> RequirementJSON:
    return type_cast(
        RequirementJSON,
        json_check_format(
            debug,
            requirement_json,
            {"package", "version"},
            set(),
            "Invalid requirement format.",
        ),
    )


def check_requirements(
    debug: bool, requirements_json: Any
) -> Iterable[RequirementJSON]:
    if type(requirements_json) is not list:
        raise MyException("Invalid requirements format.")

    for requirement_json in requirements_json:
        requirement_checked = check_requirement(debug, requirement_json)

        if type(requirement_checked["package"]) is not str:
            raise MyException("Invalid requirement format.")

        if type(requirement_checked["version"]) is not str:
            raise MyException("Invalid requirement format.")

    return requirements_json


def parse_requirements(debug: bool, requirements_json: Any) -> Set[Requirement]:
    requirements_checked = check_requirements(debug, requirements_json)

    return {
        Requirement(requirement_checked["package"], requirement_checked["version"])
        for requirement_checked in requirements_checked
    }


def check_options(debug: bool, options_json: Any) -> Options:
    options_checked = type_cast(
        Options,
        json_check_format(
            debug, options_json, set(), {"settings", "options"}, "Invalid input format."
        ),
    )

    for category_json, assignments_json in options_checked.items():
        if type(assignments_json) is not frozendict:
            raise MyException(
                f"Invalid input format. options[{category_json}] not a dict."
            )

        for assignment in assignments_json.values():
            if type(assignment) is not str:
                raise MyException(f"Invalid input format. `{assignment}` not a string.")

    return options_checked


def parse_options(debug: bool, options_json: Any) -> Options:
    options_checked = check_options(debug, options_json)

    return options_checked
