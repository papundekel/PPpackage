from asyncio import Lock, create_subprocess_exec
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
from PPpackage_utils.parse import Lockfile
from PPpackage_utils.utils import (
    Resolution,
    asubprocess_communicate,
    ensure_dir_exists,
    frozendict,
)

from .utils import (
    Options,
    Requirement,
    create_and_render_temp_file,
    get_cache_path,
    make_conan_environment,
    parse_conan_graph_nodes,
)


async def export_leaf(
    environment: Mapping[str, str],
    template: Jinja2Template,
    index: int,
    requirement_partition: Mapping[str, str],
) -> None:
    with create_and_render_temp_file(
        template, {"index": index, "requirements": requirement_partition}, ".py"
    ) as conanfile_leaf:
        process = create_subprocess_exec(
            "conan",
            "export",
            conanfile_leaf.name,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=PIPE,
            env=environment,
        )

        await asubprocess_communicate(await process, "Error in `conan export`.")


async def export_leaves(
    environment: Mapping[str, str],
    template: Jinja2Template,
    requirement_partitions: Iterable[Mapping[str, str]],
) -> None:
    for index, requirement_partition in enumerate(requirement_partitions):
        await export_leaf(environment, template, index, requirement_partition)


async def remove_leaves_from_cache(environment: Mapping[str, str]) -> None:
    process = create_subprocess_exec(
        "conan",
        "remove",
        "--confirm",
        "leaf-*/1.0.0@pppackage",
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


def parse_conan_graph_resolve(graph_string: str) -> Lockfile:
    nodes = parse_conan_graph_nodes(graph_string)

    return frozendict(
        {
            (package_and_version := node["ref"].split("/", 1))[0]: package_and_version[
                1
            ]
            for node in nodes
            if node["user"] != "pppackage"
        }
    )


async def get_lockfile(
    environment: Mapping[str, str],
    root_template: Jinja2Template,
    profile_template: Jinja2Template,
    build_profile_path: Path,
    requirement_partitions: Sequence[Mapping[str, str]],
    options: Options,
) -> Lockfile:
    with (
        create_and_render_temp_file(
            root_template,
            {"leaf_indices": range(len(requirement_partitions))},
            ".py",
        ) as root_file,
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
            root_file.name,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=None,
            env=environment,
        )

        graph_string = await asubprocess_communicate(
            await process, "Error in `conan graph info`"
        )

    lockfile = parse_conan_graph_resolve(graph_string.decode("ascii"))

    return lockfile


async def resolve(
    templates_path: Path,
    cache_path: Path,
    requirements: Iterable[Requirement],
    options: Options,
) -> Set[Resolution]:
    cache_path = get_cache_path(cache_path)

    ensure_dir_exists(cache_path)

    # CONAN_HOME must be an absolute path
    environment = make_conan_environment(cache_path)

    requirement_partitions = create_requirement_partitions(requirements)

    jinja_loader = Jinja2Environment(
        loader=Jinja2FileSystemLoader(templates_path),
        autoescape=jinja2_select_autoescape(),
    )

    leaf_template = jinja_loader.get_template("conanfile-leaf.py.jinja")
    root_template = jinja_loader.get_template("conanfile-root.py.jinja")
    profile_template = jinja_loader.get_template("profile.jinja")

    await export_leaves(environment, leaf_template, requirement_partitions)

    build_profile_path = templates_path / "profile"

    lockfile = await get_lockfile(
        environment,
        root_template,
        profile_template,
        build_profile_path,
        requirement_partitions,
        options,
    )

    await remove_leaves_from_cache(environment)

    return frozenset([Resolution(lockfile, frozendict())])
