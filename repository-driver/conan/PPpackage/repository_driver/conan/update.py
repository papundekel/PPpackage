from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from multiprocessing import cpu_count
from sys import stderr

from conan.api.conan_api import ConanAPI
from conan.api.model import Remote
from conan.internal.conan_app import ConanApp
from conans.errors import ConanException
from conans.model.recipe_ref import RecipeReference

from PPpackage.utils.lock.rw import write as rwlock_write

from .epoch import update as update_epoch
from .schemes import DriverParameters, RepositoryParameters
from .state import State


def fetch_revisions(
    api: ConanAPI, remote: Remote, recipe: RecipeReference
) -> Sequence[RecipeReference]:
    # takes too long
    # return api.list.recipe_revisions(recipe, remote)
    try:
        revision = api.list.latest_recipe_revision(recipe, remote)
    except ConanException:
        print(f"Failed to fetch revisions for {recipe}", file=stderr)
        return []
    else:
        return [revision]


def download_recipes(
    app: ConanApp, remote: Remote, revisions: Iterable[RecipeReference]
):
    for revision in revisions:
        try:
            app.cache.recipe_layout(revision)
        except ConanException:
            pass
        else:
            return

        if revision.timestamp is None:
            server_ref = app.remote_manager.get_recipe_revision_reference(
                revision, remote
            )
            assert server_ref == revision
            revision.timestamp = server_ref.timestamp  # type: ignore

        app.remote_manager.get_recipe(revision, remote)


async def update(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    remote = Remote(
        "",
        url=str(repository_parameters.url),
        verify_ssl=repository_parameters.verify_ssl,
    )

    async with rwlock_write(state.coroutine_lock, state.file_lock):
        recipes = state.api.search.recipes("*", remote)

        with ThreadPoolExecutor(cpu_count() * 16) as executor:
            futures = list[Future]()

            for revisions in executor.map(
                lambda recipe: fetch_revisions(state.api, remote, recipe), recipes
            ):
                futures.append(
                    executor.submit(download_recipes, state.app, remote, revisions)
                )

            for future in futures:
                future.result()

        update_epoch(repository_parameters.database_path / "epoch")
