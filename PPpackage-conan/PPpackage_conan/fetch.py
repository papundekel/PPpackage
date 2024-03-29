from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Iterable
from pathlib import Path

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import (
    Dependency,
    FetchRequest,
    Options,
    Package,
    ProductIDAndInfo,
)
from PPpackage_submanager.utils import jinja_render_temp_file
from PPpackage_utils.utils import asubprocess_wait
from PPpackage_utils.validation import load_object

from .lifespan import State
from .schemes import ProductInfo
from .settings import Settings
from .utils import FetchNode, make_conan_environment, parse_conan_graph_nodes


async def create_requirements(
    package: Package, dependencies: AsyncIterable[Dependency]
) -> Iterable[tuple[str, str]]:
    requirements = [(package.name, package.version)]

    async for dependency in dependencies:
        if dependency.manager == "conan" and dependency.product_info is not None:
            product_info_parsed = load_object(ProductInfo, dependency.product_info)
            requirements.append((dependency.name, product_info_parsed.version))

    return requirements


async def fetch(
    settings: Settings,
    state: State,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> ProductIDAndInfo | FetchRequest:
    environment = make_conan_environment(settings.cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(state.data_path),
        autoescape=jinja2_select_autoescape(),
    )

    conanfile_template = jinja_loader.get_template("conanfile-fetch.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    requirements = await create_requirements(package, dependencies)

    with (
        jinja_render_temp_file(
            conanfile_template, {"requirements": requirements}, ".py"
        ) as conanfile_file,
        jinja_render_temp_file(
            profile_template, {"options": options}
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)
        build_profile_path = state.data_path / "profile"

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
            stderr=None,
            env=environment,
        )

        assert process.stdout is not None
        graph_json_bytes = await process.stdout.read()

        await asubprocess_wait(process, CommandException)

    nodes = parse_conan_graph_nodes(FetchNode, graph_json_bytes)

    for node in nodes.values():
        package_name = node.name

        if package_name in package.name:
            return ProductIDAndInfo(
                product_id=node.get_product_id(),
                product_info=ProductInfo(
                    version=node.get_version(), cpp_info=node.cpp_info
                ),
            )

    raise CommandException()
