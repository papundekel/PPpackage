from collections.abc import AsyncIterable, Iterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import TranslatorInfo
from PPpackage.utils.async_ import Result

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .state import State


def fetch_revisions(
    api: ConanAPI, recipe: RecipeReference
) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def fetch_translator_data(
    state: State, epoch_result: Result[str]
) -> AsyncIterable[TranslatorInfo]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(state.database_path / "epoch"))

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
