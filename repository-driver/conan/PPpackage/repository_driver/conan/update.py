from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from itertools import cycle
from multiprocessing import cpu_count
from pathlib import Path
from sys import stderr
from typing import cast as type_cast

from conan.api.conan_api import ConanAPI
from conan.api.model import PackagesList, Remote
from conan.internal.conan_app import ConanApp
from conans.errors import ConanException
from conans.model.profile import Profile
from conans.model.recipe_ref import RecipeReference

from PPpackage.utils.file import TemporaryDirectory
from PPpackage.utils.lock.rw import write as rwlock_write

from .epoch import update as update_epoch
from .state import State
from .utils import create_api_and_app


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
        print(f"WARNING: Failed to fetch revisions for {recipe}", file=stderr)
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


def save_and_restore(
    source_api: ConanAPI, package_list: PackagesList, destination_api: ConanAPI
) -> None:
    with TemporaryDirectory() as temp:
        archive_path = temp / "packages"
        source_api.cache.save(package_list, archive_path)
        destination_api.cache.restore(archive_path)


def create_default_profile(home_path: Path, detected_profile: Profile) -> None:
    profiles_path = home_path / "profiles"
    profiles_path.mkdir(parents=True, exist_ok=True)

    with (profiles_path / "default").open("w") as profile_file:
        profile_file.write("[settings]\n")

        for setting, value in detected_profile.settings.items():
            profile_file.write(f"{setting}={value}\n")


async def update(state: State) -> None:
    remote = Remote("", url=str(state.url), verify_ssl=state.verify_ssl)

    async with rwlock_write(state.coroutine_lock, state.file_lock):
        detected_profile = state.api.profiles.detect()

        create_default_profile(Path(state.api.home_folder), detected_profile)

        recipes = state.api.search.recipes("*", remote)

        all_revisions = list[RecipeReference]()

        with ThreadPoolExecutor(cpu_count() * 16) as executor:
            futures = list[Future]()

            for revisions in executor.map(
                lambda recipe: fetch_revisions(state.api, remote, recipe), recipes
            ):
                futures.append(
                    executor.submit(download_recipes, state.app, remote, revisions)
                )

                all_revisions.extend(revisions)

            for future in futures:
                future.result()

        package_lists = [PackagesList() for _ in state.aux_home_paths]

        for revision, package_list in zip(all_revisions, cycle(package_lists)):
            package_list.add_refs([revision])

        for package_list, aux_home in zip(package_lists, state.aux_home_paths):
            aux_api, _ = create_api_and_app(aux_home)
            create_default_profile(aux_home, detected_profile)
            save_and_restore(state.api, package_list, aux_api)

        update_epoch(state.database_path / "epoch")
