from collections.abc import Mapping, Set
from sys import stderr
from typing import IO, Any

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .schemes import RequirementInput, ResolutionModel


def print_requirements(output: IO[str], requirements: RequirementInput):
    pass  # TODO


async def resolve(
    repositories: Mapping[str, Repository],
    requirements: RequirementInput,
    options: Any,
) -> Set[ResolutionModel]:
    stderr.write("Resolving requirements...\n")

    print_requirements(stderr, requirements)

    models: Set[ResolutionModel] = frozenset()

    if len(models) == 0:
        raise SubmanagerCommandFailure("No requirement resolution found.")

    stderr.write("Resolution done.\n")

    return models
