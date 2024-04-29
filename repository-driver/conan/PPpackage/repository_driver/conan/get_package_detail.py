from collections.abc import Iterable

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.client.conanfile.configure import run_configure_method
from conans.client.graph.profile_node_definer import initialize_conanfile_profile
from conans.model.options import Options as ConanOptions
from conans.model.profile import Profile
from conans.model.recipe_ref import RecipeReference
from conans.model.requires import Requirement
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    MetaOnTopProductDetail,
    PackageDetail,
)

from .schemes import DriverParameters, Options, RepositoryParameters


def get_requirements(
    app: ConanApp, revision: RecipeReference, layout
) -> Iterable[Requirement]:
    conanfile_path = layout.conanfile()
    conanfile = app.loader.load_basic(conanfile_path)

    build_profile = Profile()  # TODO
    host_profile = Profile()  # TODO

    initialize_conanfile_profile(conanfile, build_profile, host_profile, "host", False)
    run_configure_method(conanfile, ConanOptions(), host_profile.options, revision)

    return conanfile.requires.values()


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
    full_package_name: str,
) -> PackageDetail | None:
    tokens = full_package_name.split("conan-", 1)

    if len(tokens) != 2 or len(tokens[0]) != 0:
        return None

    revision = RecipeReference.loads(tokens[1])

    api = ConanAPI(str(repository_parameters.database_path / "cache"))
    app = ConanApp(api)

    try:
        layout = app.cache.recipe_layout(revision)
    except:
        return None

    return PackageDetail(
        frozenset([str(revision.name)]),
        frozenset(
            str(requirement.ref.name)
            for requirement in get_requirements(app, revision, layout)
        ),
        MetaOnTopProductDetail(ANDRequirement([])),  # TODO:build requirements
    )
