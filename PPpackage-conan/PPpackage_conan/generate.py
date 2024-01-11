from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable, Iterable
from pathlib import Path
from typing import Any

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Product
from PPpackage_utils.utils import asubprocess_wait

from .settings import Settings
from .utils import (
    State,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
)


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
    settings: Settings,
    state: State,
    options: Any,
    products: AsyncIterable[Product],
    generators: AsyncIterable[str],
    destination_path: Path,
) -> None:
    cache_path = get_cache_path(settings.cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(state.data_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-generate.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    native_generators_path_suffix = Path("conan")

    native_generators_path = destination_path / native_generators_path_suffix

    with (
        create_and_render_temp_file(
            conanfile_template,
            {
                "packages": [product async for product in products],
                "generators": [generator async for generator in generators],
            },
            ".py",
        ) as conanfile_file,
        create_and_render_temp_file(
            profile_template, {"options": options}
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)
        build_profile_path = state.data_path / "profile"

        process = await create_subprocess_exec(
            "conan",
            "install",
            "--output-folder",
            str(native_generators_path),
            "--deployer",
            state.deployer_path,
            "--build",
            "never",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            conanfile_file.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=DEVNULL,
            env=environment,
        )

        await asubprocess_wait(process, CommandException())

    patch_native_generators(native_generators_path, native_generators_path_suffix)
