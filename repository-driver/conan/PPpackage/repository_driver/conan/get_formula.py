from collections.abc import Iterable
from sys import stderr
from typing import AsyncIterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import Requirement

from PPpackage.utils.rwlock import read as rwlock_read
from PPpackage.utils.utils import Result

from .epoch import get as get_epoch
from .schemes import DriverParameters, Options, RepositoryParameters
from .state import State
from .utils import get_requirements


def get_recipes(api: ConanAPI) -> Iterable[RecipeReference]:
    return api.search.recipes("*")


def get_revisions(api: ConanAPI, recipe: RecipeReference) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def get_formula(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
    epoch_result: Result[str],
) -> AsyncIterable[list[Requirement]]:
    database_path = repository_parameters.database_path

    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(database_path / "epoch"))

        for recipe in get_recipes(state.api):
            for revision in get_revisions(state.api, recipe):
                try:
                    requirements = get_requirements(state.api, state.app, revision)
                except:
                    continue

                assert requirements is not None

                for requirement in requirements:
                    yield [
                        Requirement(
                            "noop",
                            f"conan-{revision.name}/{revision.version}#{revision.revision}",
                            False,
                        ),
                        Requirement(
                            "conan",
                            {
                                "package": str(requirement.ref.name),
                                "version": str(requirement.ref.version),
                            },
                        ),
                    ]
