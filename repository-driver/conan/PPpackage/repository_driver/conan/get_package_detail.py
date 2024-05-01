from itertools import chain

from conan.api.conan_api import ConanAPI
from conan.internal.conan_app import ConanApp
from conans.model.recipe_ref import RecipeReference
from conans.model.requires import Requirement
from PPpackage.repository_driver.interface.schemes import (
    ANDRequirement,
    MetaOnTopProductDetail,
    PackageDetail,
    SimpleRequirement,
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

    runtime_requirements = list[Requirement]()
    build_requirements = list[Requirement]()

    for requirement in requirements:
        if not requirement.build:
            runtime_requirements.append(requirement)
        else:
            build_requirements.append(requirement)

    return PackageDetail(
        frozenset([f"conan-{revision.name}"]),
        frozenset(
            f"conan-{requirement.ref.name}" for requirement in runtime_requirements
        ),
        MetaOnTopProductDetail(
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
                            for requirement in build_requirements
                        ),
                    )
                )
            )
        ),
    )
