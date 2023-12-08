from asyncio import Queue as SimpleQueue
from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Iterable, Set
from pathlib import Path
from typing import Any

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_utils.parse import (
    BuildResult,
    Dependency,
    IDAndInfo,
    Options,
    Package,
    PackageIDAndInfo,
    load_object,
)
from PPpackage_utils.submanager import (
    SubmanagerCommandFailure,
    discard_build_results_context,
)
from PPpackage_utils.utils import asubprocess_wait

from .parse import FetchProductInfo
from .utils import (
    FetchNode,
    PackagePaths,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
    parse_conan_graph_nodes,
)


async def create_requirements(
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]]
) -> tuple[Iterable[tuple[str, str]], Set[str]]:
    requirements = []
    package_names = set()

    async for package, dependencies in packages:
        requirements.append((package.name, package.version))
        package_names.add(package.name)

        async for dependency in dependencies:
            if dependency.manager == "conan" and dependency.product_info is not None:
                product_info_parsed = load_object(
                    FetchProductInfo, dependency.product_info
                )
                requirements.append((dependency.name, product_info_parsed.version))

    return requirements, package_names


async def fetch(
    debug: bool,
    package_paths: PackagePaths,
    session_data: Any,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> AsyncIterable[PackageIDAndInfo]:
    async with discard_build_results_context(build_results):
        cache_path = get_cache_path(cache_path)

        environment = make_conan_environment(cache_path)

        jinja_loader = Jinja2Environment(
            loader=Jinja2FileSystemLoader(package_paths.data_path),
            autoescape=jinja2_select_autoescape(),
        )

        conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
        profile_template = jinja_loader.get_template("profile.jinja")

        requirements, package_names = await create_requirements(packages)

        with (
            create_and_render_temp_file(
                conanfile_template, {"requirements": requirements}, ".py"
            ) as conanfile_file,
            create_and_render_temp_file(
                profile_template, {"options": options}
            ) as host_profile_file,
        ):
            host_profile_path = Path(host_profile_file.name)
            build_profile_path = package_paths.data_path / "profile"

            process = await create_subprocess_exec(
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

            assert process.stdout is not None
            graph_json_bytes = await process.stdout.read()

            await asubprocess_wait(process, SubmanagerCommandFailure())

        nodes = parse_conan_graph_nodes(debug, FetchNode, graph_json_bytes)

        for node in nodes.values():
            package_name = node.name

            if package_name in package_names:
                yield PackageIDAndInfo(
                    name=package_name,
                    id_and_info=IDAndInfo(
                        product_id=node.get_product_id(),
                        product_info=FetchProductInfo(
                            version=node.get_version(), cpp_info=node.cpp_info
                        ),
                    ),
                )
