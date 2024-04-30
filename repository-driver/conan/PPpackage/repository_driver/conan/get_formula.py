from collections.abc import Iterable
from typing import AsyncIterable

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    ImplicationRequirement,
    Requirement,
    SimpleRequirement,
)

from .schemes import DriverParameters, Options, RepositoryParameters
from .utils import get_requirements


def get_recipes(api: ConanAPI) -> Iterable[RecipeReference]:
    return api.search.recipes("*")


def get_revisions(api: ConanAPI, recipe: RecipeReference) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def get_formula(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
) -> AsyncIterable[Requirement]:
    api = ConanAPI(str(repository_parameters.database_path.absolute() / "cache"))
    app = ConanApp(api)

    for recipe in get_recipes(api):
        for revision in get_revisions(api, recipe):
            try:
                requirements = get_requirements(api, app, revision)
            except:
                continue

            assert requirements is not None

            for requirement in requirements:
                yield ImplicationRequirement(
                    SimpleRequirement(
                        "noop",
                        f"conan-{revision.name}/{revision.version}#{revision.revision}",
                    ),
                    SimpleRequirement(
                        "conan",
                        {
                            "package": str(requirement.ref.name),
                            "version": str(requirement.ref.version),
                        },
                    ),
                )
