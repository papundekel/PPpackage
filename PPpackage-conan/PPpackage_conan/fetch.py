from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable
from pathlib import Path

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.parse import (
    Dependency,
    IDAndInfo,
    Options,
    Package,
    PackageIDAndInfo,
    load_object,
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


async def fetch_send(
    templates_path: Path,
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
) -> AsyncIterable[PackageIDAndInfo]:
    cache_path = get_cache_path(cache_path)

    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    requirements = []

    async for package, dependencies in packages:
        requirements.append((package.name, package.version))

        async for dependency in dependencies:
            if dependency.manager == "conan" and dependency.product_info is not None:
                product_info_parsed = load_object(
                    FetchProductInfo, dependency.product_info
                )
                requirements.append((dependency.name, product_info_parsed.version))

    with (
        create_and_render_temp_file(
            conanfile_template, {"requirements": requirements}, ".py"
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
            stderr=DEVNULL,
            env=environment,
        )

        graph_json_bytes = await asubprocess_communicate(
            await process, "Error in `conan install`"
        )

    nodes = parse_conan_graph_nodes(debug, FetchNode, graph_json_bytes)

    for node in nodes.values():
        yield PackageIDAndInfo(
            name=node.name,
            id_and_info=IDAndInfo(
                product_id=node.get_product_id(),
                product_info=FetchProductInfo(
                    version=node.get_version(), cpp_info=node.cpp_info
                ),
            ),
        )
