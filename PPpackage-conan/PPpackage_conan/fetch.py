from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from pathlib import Path

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.parse import (
    FetchInput,
    FetchOutput,
    FetchOutputValue,
    model_validate_obj,
)
from PPpackage_utils.utils import asubprocess_communicate

from .parse import FetchProductInfo
from .utils import (
    FetchNode,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
    parse_conan_graph_nodes,
)


async def fetch(
    templates_path: Path,
    cache_path: Path,
    input: FetchInput,
) -> FetchOutput:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    packages = []

    for package, value in input.packages.items():
        packages.append((package, value.version))

    for package, product_info_raw in input.product_infos.get("conan", {}).items():
        product_info = model_validate_obj(FetchProductInfo, product_info_raw)
        packages.append((package, product_info.version))

    with (
        create_and_render_temp_file(
            conanfile_template, {"packages": packages}, ".py"
        ) as conanfile_file,
        create_and_render_temp_file(
            profile_template, {"options": input.options}
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

        graph_json_bytes = await asubprocess_communicate(
            await process, "Error in `conan install`"
        )

    nodes = parse_conan_graph_nodes(FetchNode, graph_json_bytes)

    output = {
        node.name: FetchOutputValue(
            product_id=node.get_product_id(),
            product_info=FetchProductInfo(
                version=node.get_version(), cpp_info=node.cpp_info
            ),
        )
        for node in nodes.values()
    }

    return FetchOutput(output)
