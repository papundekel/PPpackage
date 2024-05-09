from itertools import chain

from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    MetaBuildContextDetail,
    ProductInfos,
    Requirement,
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
        list(
            chain(
                [
                    Requirement("pacman", "conan"),
                    Requirement("pacman", "bash"),
                    Requirement("pacman", "coreutils"),
                    Requirement("pacman", "jq"),
                ],
                (
                    Requirement(
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
        ),
        on_top=True,
        command=[
            "bash",
            "-c",
            f"package_id=(conan install --requires {revision} --build {revision} --format json | "
            "jq '.graph.nodes.\"1\".package_id' | head -c -2 | tail -c +2)\n"
            "mkdir /mnt/output\n"
            f'conan cache save {revision}:"$package_id" --file /mnt/output/product'
            "echo -n conan > /mnt/output/installer\n",
        ],
    )
