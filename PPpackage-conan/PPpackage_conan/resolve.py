from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import (
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
from PPpackage_utils.utils import (
    ResolutionGraph,
    ResolutionGraphNodeValue,
    asubprocess_communicate,
    ensure_dir_exists,
    frozendict,
)

from .utils import (
    Node,
    Options,
    Requirement,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
    parse_conan_graph_nodes,
)


async def export_package(
    environment: Mapping[str, str],
    template: Jinja2Template,
    **template_context: Any,
) -> None:
    with create_and_render_temp_file(template, template_context, ".py") as conanfile:
        process = create_subprocess_exec(
            "conan",
            "export",
            conanfile.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=PIPE,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `conan export`.")


async def export_leaf(
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_index: int,
    index: int,
    requirement_partition: Mapping[str, str],
) -> None:
    await export_package(
        environment,
        template,
        requirement_index=requirement_index,
        index=index,
        requirements=requirement_partition,
    )


async def export_requirement(
    environment: Mapping[str, str],
    template: Jinja2Template,
    index: int,
    leaf_indices: Iterable[int],
) -> None:
    await export_package(
        environment,
        template,
        index=index,
        leaf_indices=leaf_indices,
    )


async def export_leaves(
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_index: int,
    requirement_partitions: Iterable[Mapping[str, str]],
) -> None:
    for index, requirement_partition in enumerate(requirement_partitions):
        await export_leaf(
            environment, template, requirement_index, index, requirement_partition
        )


async def remove_temporary_packages_from_cache(environment: Mapping[str, str]) -> None:
    process = create_subprocess_exec(
        "conan",
        "remove",
        "--confirm",
        "*/1.0.0@pppackage",
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=None,
        env=environment,
    )

    await asubprocess_communicate(await process, "Error in `conan remove`")


def create_requirement_partitions(
    requirements: Iterable[Requirement],
) -> Sequence[Mapping[str, str]]:
    requirement_partitions: MutableSequence[MutableMapping[str, str]] = []

    for requirement in requirements:
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


def parse_direct_dependencies(nodes: Mapping[str, Node], node: Node):
    for dependency_id, attributes in node["dependencies"].items():
        if attributes["direct"]:
            yield nodes[dependency_id]["name"]


def parse_conan_graph_resolve(graph_string: str) -> ResolutionGraph:
    requirement_prefix = "requirement-"

    nodes = parse_conan_graph_nodes(graph_string)

    roots_unsorted: Sequence[tuple[int, Set[Any]]] = []
    graph: MutableMapping[str, ResolutionGraphNodeValue] = {}

    for node in nodes.values():
        user = node["user"]
        name = node["name"]

        if user == "pppackage" and name.startswith(requirement_prefix):
            requirement_index = int(name[len(requirement_prefix) :])
            roots_unsorted.append(
                (
                    requirement_index,
                    frozenset(
                        dependency
                        for leaf_id in node["dependencies"].keys()
                        if (leaf := nodes[leaf_id])["user"] == "pppackage"
                        for dependency in parse_direct_dependencies(nodes, leaf)
                    ),
                )
            )
        elif user != "pppackage":
            version = f"{node['version']}#{node['rrev']}"

            graph[name] = ResolutionGraphNodeValue(
                version, frozenset(parse_direct_dependencies(nodes, node)), frozendict()
            )

    roots = tuple(
        [root for _, root in sorted(roots_unsorted, key=lambda pair: pair[0])]
    )

    return ResolutionGraph(roots, frozendict(graph))


async def create_graph(
    environment: Mapping[str, str],
    root_template: Jinja2Template,
    profile_template: Jinja2Template,
    build_profile_path: Path,
    requirements_list: Sequence[Any],
    options: Options,
) -> ResolutionGraph:
    with (
        create_and_render_temp_file(
            root_template,
            {"requirement_indices": range(len(requirements_list))},
            ".py",
        ) as requirement_file,
        create_and_render_temp_file(
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
            stderr=None,
            env=environment,
        )

        graph_string = await asubprocess_communicate(
            await process, "Error in `conan graph info`"
        )

    graph = parse_conan_graph_resolve(graph_string.decode("ascii"))

    return graph


async def resolve(
    templates_path: Path,
    cache_path: Path,
    requirements_list: Sequence[Set[Requirement]],
    options: Options,
) -> Set[ResolutionGraph]:
    cache_path = get_cache_path(cache_path)

    ensure_dir_exists(cache_path)

    # CONAN_HOME must be an absolute path
    environment = make_conan_environment(cache_path)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    leaf_template = jinja_loader.get_template("conanfile-leaf.py.jinja")
    requirement_template = jinja_loader.get_template("conanfile-requirement.py.jinja")
    root_template = jinja_loader.get_template("conanfile-root.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    build_profile_path = templates_path / "profile"

    for requirement_index, requirements in enumerate(requirements_list):
        requirement_partitions = create_requirement_partitions(requirements)

        leaves_task = export_leaves(
            environment, leaf_template, requirement_index, requirement_partitions
        )

        requirement_task = export_requirement(
            environment,
            requirement_template,
            requirement_index,
            range(len(requirement_partitions)),
        )

        await leaves_task
        await requirement_task

    graph = await create_graph(
        environment,
        root_template,
        profile_template,
        build_profile_path,
        requirements_list,
        options,
    )

    await remove_temporary_packages_from_cache(environment)

    return frozenset([graph])
