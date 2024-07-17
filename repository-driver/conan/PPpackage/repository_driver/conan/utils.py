from collections.abc import Iterable
from pathlib import Path

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.client.conanfile.configure import run_configure_method
from conans.client.graph.graph import CONTEXT_HOST, RECIPE_VIRTUAL, Node
from conans.client.graph.profile_node_definer import initialize_conanfile_profile
from conans.model.options import Options as ConanOptions
from conans.model.recipe_ref import RecipeReference
from conans.model.requires import Requirement


def get_requirements(
    api: ConanAPI, app: ConanApp, revision: RecipeReference, system: bool = False
) -> tuple[Iterable[Requirement] | None, Iterable[str]]:
    try:
        layout = app.cache.recipe_layout(revision)
    except:
        return None, []

    conanfile_path = layout.conanfile()
    conanfile = app.loader.load_conanfile(conanfile_path, revision)

    Node(ref=None, conanfile=conanfile, context=CONTEXT_HOST, recipe=RECIPE_VIRTUAL)

    build_profile = api.profiles.get_profile([api.profiles.get_default_build()])  # TODO
    host_profile = api.profiles.get_profile([api.profiles.get_default_host()])  # TODO

    initialize_conanfile_profile(conanfile, build_profile, host_profile, "host", False)
    run_configure_method(conanfile, ConanOptions(), host_profile.options, revision)

    requirements = conanfile.requires.values()

    if system and hasattr(conanfile, "system_requirements"):
        conanfile.system_requirements()

        system_requirements = conanfile.system_requires.get("pacman", {}).get(
            "install", []
        )

        return requirements, system_requirements

    return requirements, []


def create_api_and_app(home_path: Path):
    api = ConanAPI(str(home_path.absolute()))
    app = ConanApp(api)

    return api, app
