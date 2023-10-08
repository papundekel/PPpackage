from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable, Mapping
from pathlib import Path

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.utils import asubprocess_communicate

from .generators import additional as additional_generators
from .utils import (
    GraphInfo,
    Options,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
    parse_conan_graph_nodes,
)


def parse_conan_graph_fetch(input: str) -> Mapping[str, GraphInfo]:
    nodes = parse_conan_graph_nodes(input)

    return {node["ref"].split("/", 1)[0]: GraphInfo(node) for node in nodes}


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


async def fetch(
    templates_path: Path,
    deployer_path: Path,
    cache_path: Path,
    lockfile: Mapping[str, str],
    options: Options,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    native_generators_path_suffix = Path("conan")
    native_generators_path = generators_path / native_generators_path_suffix

    with (
        create_and_render_temp_file(
            conanfile_template,
            {
                "lockfile": lockfile,
                "generators": generators - additional_generators.keys(),
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
            "missing",
            "--format",
            "json",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            conanfile_file.name,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=None,
            env=environment,
        )

        graph_json = await asubprocess_communicate(
            await process, "Error in `conan install`"
        )

    graph_infos = parse_conan_graph_fetch(graph_json.decode("ascii"))

    patch_native_generators(native_generators_path, native_generators_path_suffix)

    for generator in generators & additional_generators.keys():
        additional_generators[generator](generators_path, graph_infos)

    product_ids = {
        package: graph_info.product_id for package, graph_info in graph_infos.items()
    }

    return product_ids
