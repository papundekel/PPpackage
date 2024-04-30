from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    MetaOnTopProductDetail,
    PackageDetail,
)

from .schemes import DriverParameters, Options, RepositoryParameters
from .utils import PREFIX, get_requirements


async def get_package_detail(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    revision = RecipeReference.loads(full_package_name[len(PREFIX) :])

    api = ConanAPI(str(repository_parameters.database_path.absolute() / "cache"))
    app = ConanApp(api)

    requirements = get_requirements(api, app, revision)

    if requirements is None:
        return None

    return PackageDetail(
        frozenset([f"conan-{revision.name}"]),
        frozenset(f"conan-{requirement.ref.name}" for requirement in requirements),
        MetaOnTopProductDetail(ANDRequirement([])),  # TODO:build requirements
    )
