from itertools import chain

from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import PackageDetail

from .schemes import Options
from .state import State
from .utils import get_requirements


async def get_package_detail(
    state: State, translated_options: Options, full_package_name: str
) -> PackageDetail | None:
    if not full_package_name.startswith("conan-"):
        return None

    revision = RecipeReference.loads(full_package_name[len("conan-") :])

    requirements, system_requirements = get_requirements(
        state.api, state.app, revision, system=True
    )

    if requirements is None:
        return None

    return PackageDetail(
        frozenset([f"conan-{revision.name}"]),
        frozenset(
            chain(
                (
                    f"conan-{requirement.ref.name}"
                    for requirement in requirements
                    if not requirement.build
                ),
                (f"pacman-{requirement}" for requirement in system_requirements),
            )
        ),
    )
