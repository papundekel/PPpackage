from os import environ
from string import Template
from typing import Any

from pydantic import AfterValidator


def _substitute_environment_variables(value: Any):
    value_string = str(value)

    substituted_value = Template(value_string).safe_substitute(environ)

    return type(value)(substituted_value)


WithVariables = AfterValidator(_substitute_environment_variables)
