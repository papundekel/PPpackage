from itertools import chain

from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    BuildContextDetail,
    MetaBuildContextDetail,
    ProductInfos,
    SimpleRequirement,
)

from .schemes import DriverParameters, Options, RepositoryParameters
from .state import State
from .utils import PREFIX, get_requirements


async def get_build_context(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: Options,
    package: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    if not package.startswith(PREFIX):
        raise Exception(f"Invalid package name: {package}")

    revision = RecipeReference.loads(package[len(PREFIX) :])

    requirements = get_requirements(state.api, state.app, revision)

    if requirements is None:
        raise Exception(f"Recipe not found: {revision}")

    return MetaBuildContextDetail(
        ANDRequirement(
            list(
                chain(
                    [SimpleRequirement("pacman", "conan")],
                    (
                        SimpleRequirement(
                            "conan",
                            {
                                "package": str(requirement.ref.name),
                                "version": str(requirement.ref.version),
                            },
                        )
                        for requirement in requirements
                        if requirement.build
                    ),
                )
            )
        ),
        options=None,
        on_top=True,
    )
