from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import PackageDetail

from .schemes import DriverParameters, Options, RepositoryParameters
from .state import State
from .utils import PREFIX, get_requirements


async def get_package_detail(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    revision = RecipeReference.loads(full_package_name[len(PREFIX) :])

    requirements = get_requirements(state.api, state.app, revision)

    if requirements is None:
        return None

    return PackageDetail(
        frozenset([f"conan-{revision.name}"]),
        frozenset(
            f"conan-{requirement.ref.name}"
            for requirement in requirements
            if not requirement.build
        ),
    )
