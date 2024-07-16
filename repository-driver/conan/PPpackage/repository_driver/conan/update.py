from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import ExitStack
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


def restore(home_path: Path, archive_path: Path) -> None:
    api, _ = create_api_and_app(home_path)

    api.cache.restore(archive_path)


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

        for aux_home in state.aux_home_paths:
            create_default_profile(aux_home, detected_profile)

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

        with ExitStack() as exit_stack:
            archive_paths = list[Path]()

            for package_list in package_lists:
                archive_path = (
                    exit_stack.enter_context(TemporaryDirectory()) / "packages"
                )

                state.api.cache.save(package_list, archive_path)
                archive_paths.append(archive_path)

            with ProcessPoolExecutor() as executor:
                futures = []

                for archive_path, aux_home in zip(archive_paths, state.aux_home_paths):
                    future = executor.submit(restore, aux_home, archive_path)
                    futures.append(future)

                for future in futures:
                    future.result()

        update_epoch(state.database_path / "epoch")
