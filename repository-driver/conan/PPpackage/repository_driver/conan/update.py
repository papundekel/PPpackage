from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path
from sys import stderr
from typing import cast as type_cast

from conan.api.conan_api import ConanAPI
from conan.api.model import Remote
from conan.internal.conan_app import ConanApp
from conans.errors import ConanException
from conans.model.recipe_ref import RecipeReference

from PPpackage.utils.lock.rw import write as rwlock_write

from .epoch import update as update_epoch
from .state import State


def fetch_revisions(
    api: ConanAPI, remote: Remote, recipe: RecipeReference
) -> Sequence[RecipeReference]:
    # this takes too long:
    # return api.list.recipe_revisions(recipe, remote)

    try:
        revision = type_cast(
            RecipeReference, api.list.latest_recipe_revision(recipe, remote)
        )
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


async def update(state: State) -> None:
    remote = Remote("", url=str(state.url), verify_ssl=state.verify_ssl)

    async with rwlock_write(state.coroutine_lock, state.file_lock):
        detected_profile = state.api.profiles.detect()

        profiles_path = Path(state.api.home_folder) / "profiles"

        profiles_path.mkdir(parents=True, exist_ok=True)

        with (profiles_path / "default").open("w") as profile_file:
            profile_file.write("[settings]\n")

            for setting, value in detected_profile.settings.items():
                profile_file.write(f"{setting}={value}\n")

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

        update_epoch(state.database_path / "epoch")
