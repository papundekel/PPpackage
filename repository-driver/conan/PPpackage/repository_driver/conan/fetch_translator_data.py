from collections.abc import AsyncIterable, Iterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import TranslatorInfo

from PPpackage.utils.rwlock import read as rwlock_read
from PPpackage.utils.utils import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State


def fetch_revisions(
    api: ConanAPI, recipe: RecipeReference
) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def fetch_translator_data(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    epoch_result: Result[str],
) -> AsyncIterable[TranslatorInfo]:
    database_path = repository_parameters.database_path

    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(database_path / "epoch"))

        recipes = state.api.search.recipes("*")
        for recipe in recipes:
            for revision in fetch_revisions(state.api, recipe):
                yield TranslatorInfo(
                    f"conan-{revision.name}",
                    {
                        "version": str(revision.version),
                        "revision": str(revision.revision),
                    },
                )
