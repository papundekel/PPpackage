from collections.abc import Set
from typing import Any

from PPpackage_utils.utils import MyException


def check_requirements(input: Any) -> list[str]:
    if type(input) is not list:
        raise MyException("Invalid requirements format")

    for requirement_input in input:
        if type(requirement_input) is not str:
            raise MyException("Invalid requirements format")

    return input


def parse_requirements(debug: bool, input: Any) -> Set[str]:
    input_checked = check_requirements(input)

    requirements = input_checked

    return set(requirements)
