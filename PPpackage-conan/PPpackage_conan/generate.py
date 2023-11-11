from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import Iterable, Mapping, Set
from pathlib import Path
from typing import Any

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.parse import GenerateInputPackagesValue
from PPpackage_utils.utils import asubprocess_communicate

from .utils import create_and_render_temp_file, get_cache_path, make_conan_environment


def patch_native_generators_paths(
    old_generators_path: Path,
    new_generators_path: Path,
    files_to_patch_paths: Iterable[Path],
) -> None:
    old_generators_path_abs_str = str(old_generators_path.absolute())
    new_generators_path_str = str(new_generators_path)

    for file_to_patch_path in files_to_patch_paths:
        if file_to_patch_path.exists():
            with open(file_to_patch_path, "r") as file_to_patch:
                lines = file_to_patch.readlines()

            lines = [
                line.replace(old_generators_path_abs_str, new_generators_path_str)
                for line in lines
            ]

            with open(file_to_patch_path, "w") as file_to_patch:
                file_to_patch.writelines(lines)


def patch_native_generators(
    native_generators_path: Path, native_generators_path_suffix: Path
) -> None:
    new_generators_path = Path("/PPpackage/generators") / native_generators_path_suffix

    patch_native_generators_paths(
        native_generators_path,
        new_generators_path,
        [
            native_generators_path / file_sub_path
            for file_sub_path in [Path("CMakePresets.json")]
        ],
    )


async def generate(
    templates_path: Path,
    deployer_path: Path,
    cache_path: Path,
    generators: Set[str],
    generators_path: Path,
    options: Any,
    packages: Mapping[str, GenerateInputPackagesValue],
) -> None:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-generate.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    native_generators_path_suffix = Path("conan")
    native_generators_path = generators_path / native_generators_path_suffix

    with (
        create_and_render_temp_file(
            conanfile_template,
            {
                "packages": (
                    (package, attribute.version, attribute.product_id)
                    for package, attribute in packages.items()
                ),
                "generators": generators,
            },
            ".py",
        ) as conanfile_file,
        create_and_render_temp_file(
            profile_template, {"options": options}
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)
        build_profile_path = templates_path / "profile"

        process = create_subprocess_exec(
            "conan",
            "install",
            "--output-folder",
            str(native_generators_path),
            "--deployer",
            deployer_path,
            "--build",
            "never",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            conanfile_file.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=None,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `conan install`")

    patch_native_generators(native_generators_path, native_generators_path_suffix)
