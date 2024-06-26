from collections.abc import Mapping
from itertools import chain
from typing import Any

from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    BuildContextInfo,
    ProductInfo,
    ProductInfos,
)
from pydantic import ValidationError

from .schemes import ConanProductInfo, Options
from .state import State


def create_ref(
    dependency: str, product_infos: Mapping[str, Any]
) -> RecipeReference | None:
    try:
        conan_product_info = ConanProductInfo.model_validate(
            next(iter(product_infos.values()))
        )
    except ValidationError:
        return None

    return RecipeReference(
        name=dependency[len("conan-") :],
        version=conan_product_info.version,
        revision=conan_product_info.revision,
    )


async def compute_product_info(
    state: State,
    translated_options: Options,
    package: str,
    build_context_info: BuildContextInfo,
    runtime_product_infos: ProductInfos,
) -> ProductInfo:
    if not package.startswith("conan-"):
        raise Exception(f"Invalid package name: {package}")

    revision = RecipeReference.loads(package[len("conan-") :])

    api = state.api

    build_profile = api.profiles.get_profile([api.profiles.get_default_build()])  # TODO
    host_profile = api.profiles.get_profile([api.profiles.get_default_host()])  # TODO

    graph = api.graph.load_graph_requires(
        list(
            chain(
                [revision],
                (
                    ref
                    for dependency, product_infos in runtime_product_infos.items()
                    if (ref := create_ref(dependency, product_infos)) is not None
                ),
            )
        ),
        profile_build=build_profile,
        profile_host=host_profile,
        tool_requires=[],
        lockfile=None,
        remotes=[],
        update=False,
    )

    api.graph.analyze_binaries(graph, remotes=[])

    node = graph.by_levels()[-2][0]

    return {
        f"conan-{revision.name}": ConanProductInfo(
            version=str(revision.version),
            revision=str(revision.revision),
            package_id=node.package_id,
        ).model_dump()
    }
