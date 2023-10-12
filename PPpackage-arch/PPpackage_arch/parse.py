from collections.abc import Iterable, Set
from typing import Any

from PPpackage_utils.utils import MyException


def check_requirements(requirements_json: Any) -> Iterable[str]:
    if type(requirements_json) is not list:
        raise MyException("Invalid requirements format")

    for requirement_json in requirements_json:
        if type(requirement_json) is not str:
            raise MyException("Invalid requirements format")

    return requirements_json


def parse_requirements(debug: bool, requirements_json: Any) -> Set[str]:
    requirements_checked = check_requirements(requirements_json)

    requirements = set(requirements_checked)

    return requirements
