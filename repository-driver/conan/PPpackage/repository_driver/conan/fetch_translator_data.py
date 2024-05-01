from collections.abc import AsyncIterable, Iterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.exceptions import EpochException
from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from .get_epoch import get_epoch
from .schemes import DriverParameters, RepositoryParameters


def fetch_revisions(
    api: ConanAPI, recipe: RecipeReference
) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def fetch_translator_data(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch: str,
) -> AsyncIterable[TranslatorInfo]:
    if epoch != await get_epoch(driver_parameters, repository_parameters):
        raise EpochException

    api = ConanAPI(str(repository_parameters.database_path.absolute() / "cache"))
    recipes = api.search.recipes("*")
    for recipe in recipes:
        for revision in fetch_revisions(api, recipe):
            yield TranslatorInfo(
                f"conan-{revision.name}",
                {"version": str(revision.version), "revision": str(revision.revision)},
            )
