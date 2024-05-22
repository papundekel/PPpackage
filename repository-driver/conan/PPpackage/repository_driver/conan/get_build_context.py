from itertools import chain

from conans.model.recipe_ref import RecipeReference
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    MetaBuildContextDetail,
    ProductInfos,
    Requirement,
)

from .schemes import Options
from .state import State
from .utils import get_requirements


async def get_build_context(
    state: State,
    translated_options: Options,
    package: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    if not package.startswith("conan-"):
        raise Exception(f"Invalid package name: {package}")

    revision = RecipeReference.loads(package[len("conan-") :])

    requirements, _ = get_requirements(state.api, state.app, revision)

    if requirements is None:
        raise Exception(f"Recipe not found: {revision}")

    full_revision = f"{revision}#{revision.revision}"

    return MetaBuildContextDetail(
        list(
            chain(
                [
                    Requirement("pacman", {"package": "conan", "no_provide": None}),
                    Requirement(
                        "pacman", {"package": "ca-certificates", "no_provide": None}
                    ),
                    Requirement("pacman", "gcc"),
                    Requirement("pacman", "cmake"),
                    Requirement("pacman", "make"),
                    Requirement("pacman", "perl"),
                    Requirement("pacman", "grep"),
                    Requirement("pacman", "sed"),
                    Requirement("pacman", "awk"),
                    Requirement("pacman", "diffutils"),
                    Requirement("pacman", "bash"),
                    Requirement("pacman", "coreutils"),
                    Requirement("pacman", "jq"),
                    Requirement("pacman", "yq"),
                    Requirement("pacman", "pacman"),
                    Requirement("pacman", "pkg-config"),
                    Requirement("pacman", "python-setuptools"),
                ],
                (
                    Requirement(
                        "conan",
                        {
                            "package": str(requirement.ref.name),
                            "version": version,
                        },
                    )
                    for requirement in requirements
                    if requirement.build
                    and (version := str(requirement.ref.version)) != "<host_version>"
                ),
            )
        ),
        on_top=True,
        command=[
            "bash",
            "-c",
            "mkdir /mnt/output\n"
            "echo -n conan > /mnt/output/installer || exit 40\n"
            "set -o pipefail\n"
            "conan profile detect\n"
            'yq --yaml-roundtrip --in-place \'.compiler.gcc.version += ["14", "14.1"]\' ~/.conan2/settings.yml || exit 10\n'
            f"if ! package_id=$(conan install --requires {full_revision} --build {full_revision} --format json | "
            "jq '.graph.nodes.\"1\".package_id' | head -c -2 | tail -c +2); then chown -R root:root ~/.conan2; exit 20; fi\n"
            "chown -R root:root ~/.conan2 || exit 50\n"
            f'conan cache save {full_revision}:"$package_id" --file /mnt/output/product || exit 30',
        ],
    )
