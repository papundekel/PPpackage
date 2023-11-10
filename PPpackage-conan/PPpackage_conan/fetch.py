from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping
from pathlib import Path

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.utils import asubprocess_communicate

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

    return {node["ref"].split("/", 1)[0]: GraphInfo(node) for node in nodes.values()}


async def fetch(
    templates_path: Path,
    cache_path: Path,
    lockfile: Mapping[str, str],
    options: Options,
) -> Mapping[str, str]:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    with (
        create_and_render_temp_file(
            conanfile_template, {"packages": lockfile.items()}, ".py"
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

    product_ids = {
        package: graph_info.product_id for package, graph_info in graph_infos.items()
    }

    return product_ids
