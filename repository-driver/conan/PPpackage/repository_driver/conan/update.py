from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from multiprocessing import cpu_count

from conan.api.conan_api import ConanAPI
from conan.api.model import Remote
from conan.internal.conan_app import ConanApp
from conans.errors import ConanException
from conans.model.recipe_ref import RecipeReference

from .epoch import update as update_epoch
from .schemes import DriverParameters, RepositoryParameters


def fetch_revisions(
    api: ConanAPI, remote: Remote, recipe: RecipeReference
) -> Sequence[RecipeReference]:
    # return api.list.recipe_revisions(recipe, remote)
    return [api.list.latest_recipe_revision(recipe, remote)]


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
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
) -> None:
    with update_epoch(repository_parameters.database_path / "database.sqlite"):
        api = ConanAPI(str(repository_parameters.database_path / "cache"))
        remote = Remote(
            "",
            url=str(repository_parameters.url),
            verify_ssl=repository_parameters.verify_ssl,
        )

        recipes = api.search.recipes("*", remote)
        app = ConanApp(api)

        with ThreadPoolExecutor(cpu_count() * 16) as executor:
            futures = list[Future]()

            for revisions in executor.map(
                lambda recipe: fetch_revisions(api, remote, recipe), recipes
            ):
                futures.append(
                    executor.submit(download_recipes, app, remote, revisions)
                )

            for future in futures:
                future.result()
