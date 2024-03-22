from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import (
    AsyncIterable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
    Set,
)
from pathlib import Path
from typing import Any, Optional
from typing import cast as typing_cast

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import Template as Jinja2Template
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Options, ResolutionGraph, ResolutionGraphNode
from PPpackage_submanager.utils import jinja_render_temp_file
from PPpackage_utils.utils import (
    asubprocess_communicate,
    asubprocess_wait,
    ensure_dir_exists,
)

from .lifespan import State
from .schemes import Requirement
from .settings import Settings
from .update_database import update_database_impl
from .utils import ResolveNode, make_conan_environment, parse_conan_graph_nodes


async def export_package(
    debug: bool,
    environment: Mapping[str, str],
    template: Jinja2Template,
    **template_context: Any,
) -> None:
    with jinja_render_temp_file(template, template_context, ".py") as conanfile:
        process = create_subprocess_exec(
            "conan",
            "export",
            conanfile.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=DEVNULL,
            env=environment,
        )

        await asubprocess_wait(await process, CommandException())


async def export_leaf(
    debug: bool,
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_index: int,
    index: int,
    requirement_partition: Mapping[str, str],
) -> None:
    await export_package(
        debug,
        environment,
        template,
        requirement_index=requirement_index,
        index=index,
        requirements=requirement_partition,
    )


async def export_requirement(
    debug: bool,
    environment: Mapping[str, str],
    template: Jinja2Template,
    index: int,
    leaf_indices: Iterable[int],
) -> None:
    await export_package(
        debug,
        environment,
        template,
        index=index,
        leaf_indices=leaf_indices,
    )


async def export_leaves(
    debug: bool,
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_index: int,
    requirement_partitions: Iterable[Mapping[str, str]],
) -> None:
    for index, requirement_partition in enumerate(requirement_partitions):
        await export_leaf(
            debug,
            environment,
            template,
            requirement_index,
            index,
            requirement_partition,
        )


async def remove_temporary_packages_from_cache(
    debug: bool, environment: Mapping[str, str]
) -> None:
    process = create_subprocess_exec(
        "conan",
        "remove",
        "--confirm",
        "*/1.0.0@pppackage",
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
        env=environment,
    )

    await asubprocess_wait(await process, CommandException())


async def create_requirement_partitions(
    requirements: AsyncIterable[Requirement],
) -> Sequence[Mapping[str, str]]:
    requirement_partitions: MutableSequence[MutableMapping[str, str]] = []

    async for requirement in requirements:
        partition_available: Optional[MutableMapping[str, str]] = next(
            (
                partition
                for partition in requirement_partitions
                if requirement.package not in partition
            ),
            None,
        )

        if partition_available is None:
            partition_available = typing_cast(MutableMapping[str, str], {})
            requirement_partitions.append(partition_available)

        partition_available[requirement.package] = requirement.version

    return requirement_partitions


def parse_direct_dependencies(nodes: Mapping[str, ResolveNode], node: ResolveNode):
    for dependency_id, attributes in node.dependencies.items():
        if attributes.direct:
            yield nodes[dependency_id].name


def parse_conan_graph_resolve(
    debug: bool, conan_graph_json_bytes: bytes
) -> ResolutionGraph:
    requirement_prefix = "requirement-"

    nodes = parse_conan_graph_nodes(debug, ResolveNode, conan_graph_json_bytes)

    roots_unsorted: Sequence[tuple[int, Set[Any]]] = []
    graph: MutableSequence[ResolutionGraphNode] = []

    for node in nodes.values():
        user = node.user
        name = node.name

        if user == "pppackage" and name.startswith(requirement_prefix):
            requirement_index = int(name[len(requirement_prefix) :])
            roots_unsorted.append(
                (
                    requirement_index,
                    {
                        dependency
                        for leaf_id in node.dependencies.keys()
                        if (leaf := nodes[leaf_id]).user == "pppackage"
                        for dependency in parse_direct_dependencies(nodes, leaf)
                    },
                )
            )
        elif user != "pppackage":
            graph.append(
                ResolutionGraphNode(
                    name,
                    node.get_version(),
                    parse_direct_dependencies(nodes, node),
                    [],
                )
            )

    roots = [root for _, root in sorted(roots_unsorted, key=lambda pair: pair[0])]

    return ResolutionGraph(roots, graph)


async def create_graph(
    debug: bool,
    environment: Mapping[str, str],
    root_template: Jinja2Template,
    profile_template: Jinja2Template,
    build_profile_path: Path,
    options: Options,
    requirements_list_length: int,
) -> ResolutionGraph:
    with (
        jinja_render_temp_file(
            root_template,
            {"requirement_indices": range(requirements_list_length)},
            ".py",
        ) as requirement_file,
        jinja_render_temp_file(
            profile_template, {"options": options}
        ) as host_profile_file,
    ):
        host_profile_path = Path(host_profile_file.name)

        process = create_subprocess_exec(
            "conan",
            "graph",
            "info",
            "--format",
            "json",
            f"--profile:host={host_profile_path}",
            f"--profile:build={build_profile_path}",
            requirement_file.name,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=DEVNULL,
            env=environment,
        )

        conan_graph_json_bytes = await asubprocess_communicate(
            await process, "Error in `conan graph info`"
        )

    graph = parse_conan_graph_resolve(debug, conan_graph_json_bytes)

    return graph


async def resolve(
    settings: Settings,
    state: State,
    options: Options,
    requirements_list: AsyncIterable[AsyncIterable[Requirement]],
) -> AsyncIterable[ResolutionGraph]:
    ensure_dir_exists(settings.cache_path)

    environment = make_conan_environment(settings.cache_path)

    if not (settings.cache_path / Path("p")).exists():
        await update_database_impl(environment)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(state.data_path),
        autoescape=jinja2_select_autoescape(),
    )

    leaf_template = jinja_loader.get_template("conanfile-leaf.py.jinja")
    requirement_template = jinja_loader.get_template("conanfile-requirement.py.jinja")
    root_template = jinja_loader.get_template("conanfile-root.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    build_profile_path = state.data_path / "profile"

    requirement_index = 0

    async for requirements in requirements_list:
        requirement_partitions = await create_requirement_partitions(requirements)

        async with TaskGroup() as group:
            group.create_task(
                export_leaves(
                    settings.debug,
                    environment,
                    leaf_template,
                    requirement_index,
                    requirement_partitions,
                )
            )

            group.create_task(
                export_requirement(
                    settings.debug,
                    environment,
                    requirement_template,
                    requirement_index,
                    range(len(requirement_partitions)),
                )
            )

        requirement_index += 1

    requirements_length = requirement_index

    graph = await create_graph(
        settings.debug,
        environment,
        root_template,
        profile_template,
        build_profile_path,
        options,
        requirements_length,
    )

    await remove_temporary_packages_from_cache(settings.debug, environment)

    yield graph
