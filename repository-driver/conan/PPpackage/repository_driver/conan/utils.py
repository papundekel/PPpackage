from collections.abc import Iterable

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.client.conanfile.configure import run_configure_method
from conans.client.graph.profile_node_definer import initialize_conanfile_profile
from conans.model.options import Options as ConanOptions
from conans.model.recipe_ref import RecipeReference
from conans.model.requires import Requirement

PREFIX = "conan-"


def get_requirements(
    api: ConanAPI, app: ConanApp, revision: RecipeReference
) -> Iterable[Requirement] | None:
    try:
        layout = app.cache.recipe_layout(revision)
    except:
        return None

    conanfile_path = layout.conanfile()
    conanfile = app.loader.load_conanfile(conanfile_path, revision)

    build_profile = api.profiles.get_profile([api.profiles.get_default_build()])  # TODO
    host_profile = api.profiles.get_profile([api.profiles.get_default_host()])  # TODO

    initialize_conanfile_profile(conanfile, build_profile, host_profile, "host", False)
    run_configure_method(conanfile, ConanOptions(), host_profile.options, revision)

    return conanfile.requires.values()
