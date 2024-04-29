from collections.abc import AsyncIterable, Iterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference

from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .schemes import DriverParameters, RepositoryParameters


def fetch_revisions(
    api: ConanAPI, recipe: RecipeReference
) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> AsyncIterable[TranslatorInfo]:
    api = ConanAPI(str(repository_parameters.database_path / "cache"))
    recipes = api.search.recipes("*")
    for recipe in recipes:
        for revision in fetch_revisions(api, recipe):
            yield TranslatorInfo(
                f"conan-{revision.name}",
                {"version": str(revision.version), "revision": str(revision.revision)},
            )
