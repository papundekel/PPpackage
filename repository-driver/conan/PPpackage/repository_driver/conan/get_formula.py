from collections.abc import Iterable
from typing import AsyncIterable

from conan.api.conan_api import ConanAPI
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import Requirement
from PPpackage.utils.async_ import Result

from PPpackage.utils.lock.rw import read as rwlock_read

from .epoch import get as get_epoch
from .schemes import Options
from .state import State
from .utils import get_requirements


def get_recipes(api: ConanAPI) -> Iterable[RecipeReference]:
    return api.search.recipes("*")


def get_revisions(api: ConanAPI, recipe: RecipeReference) -> Iterable[RecipeReference]:
    return api.list.recipe_revisions(recipe)


async def get_formula(
    state: State, translated_options: Options, epoch_result: Result[str]
) -> AsyncIterable[list[Requirement]]:
    async with rwlock_read(state.coroutine_lock, state.file_lock):
        epoch_result.set(get_epoch(state.database_path / "epoch"))

        for recipe in get_recipes(state.api):
            for revision in get_revisions(state.api, recipe):
                try:
                    requirements, system_requirements = get_requirements(
                        state.api, state.app, revision, system=True
                    )
                except:
                    continue

                assert requirements is not None

                revision_requirement = Requirement(
                    "noop",
                    f"conan-{revision.name}/{revision.version}#{revision.revision}",
                    False,
                )

                for requirement in requirements:
                    if not requirement.build:
                        yield [
                            revision_requirement,
                            Requirement(
                                "conan",
                                {
                                    "package": str(requirement.ref.name),
                                    "version": str(requirement.ref.version),
                                },
                            ),
                        ]

                for requirement in system_requirements:
                    yield [revision_requirement, Requirement("pacman", requirement)]
