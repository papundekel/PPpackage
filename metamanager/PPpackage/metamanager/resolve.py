from collections.abc import Mapping, Set
from sys import stderr
from typing import IO, Any

from PPpackage.repository_driver.interface.schemes import (
    Requirements,
    SimpleRequirement,
)

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .schemes import ResolutionModel


def print_requirements_recursion(output: IO[str], requirements: Requirements):
    if isinstance(requirements, SimpleRequirement):
        output.write(f"{requirements.translator}::{requirements.value}")
    else:
        output.write("(")
        operator = " & " if requirements.operation == "and" else " | "
        i = iter(requirements.operands)

        print_requirements_recursion(output, next(i))

        for operand in i:
            output.write(operator)
            print_requirements_recursion(output, operand)

        output.write(")")


def print_requirements(output: IO[str], requirements: Requirements):
    print_requirements_recursion(output, requirements)
    output.write("\n")


async def resolve(
    repositories: Mapping[str, Repository],
    requirements: Requirements,
    options: Any,
) -> Set[ResolutionModel]:
    stderr.write("Resolving requirements...\n")

    print_requirements(stderr, requirements)

    models: Set[ResolutionModel] = frozenset()

    if len(models) == 0:
        raise SubmanagerCommandFailure("No requirement resolution found.")

    stderr.write("Resolution done.\n")

    return models
