from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Iterable, Mapping, Set
from logging import getLogger
from pathlib import Path
from sys import stderr

from networkx import MultiDiGraph, nx_pydot
from PPpackage_arch.settings import Settings
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import (
    Lock,
    Options,
    ResolutionGraph,
    ResolutionGraphNode,
)
from PPpackage_utils.utils import asubprocess_communicate, asubprocess_wait
from pydot import graph_from_dot_data

from .settings import Settings
from .update_database import update_database
from .utils import get_cache_paths

logger = getLogger(__name__)


async def resolve_requirement(
    database_path: Path, requirement: str
) -> tuple[MultiDiGraph, str]:
    process = await create_subprocess_exec(
        "pactree",
        "--dbpath",
        str(database_path),
        "--sync",
        "--graph",
        requirement,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=PIPE,
    )

    assert process.stdout is not None
    graph_bytes = await process.stdout.read()

    graph_string = graph_bytes.decode()

    dot = graph_from_dot_data(graph_string)

    if dot is None:
        raise CommandException

    graph: MultiDiGraph = nx_pydot.from_pydot(dot[0])

    root = clean_graph(graph)

    await asubprocess_wait(process, CommandException)

    return graph, root


def get_graph_root(graph: MultiDiGraph) -> str:
    for edge in graph.out_edges("START"):
        return edge[1]

    raise CommandException


def clean_graph(graph: MultiDiGraph) -> str:
    root = get_graph_root(graph)

    nodes_to_remove = {"START", "\\n"}
    edges_to_add = set()

    for edge in graph.edges(data=True):
        data = edge[2]
        if data.get("arrowhead") == "none":
            nodes_to_remove.add(edge[0])
            for node in graph.in_edges(edge[0]):
                edges_to_add.add((node[0], edge[1]))

    graph.add_edges_from(edges_to_add)
    graph.remove_nodes_from(nodes_to_remove)

    return root


async def resolve_versions(
    database_path: Path, packages: Iterable[str]
) -> Mapping[str, str]:
    process = await create_subprocess_exec(
        "pacinfo",
        "--dbpath",
        str(database_path),
        "--short",
        *packages,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=PIPE,
    )

    stdout = await asubprocess_communicate(process, "Error in `pacinfo`.")

    lockfile = {
        (split_line := line.split())[0].split("/")[-1]: split_line[1].rsplit("-", 1)[0]
        for line in stdout.decode().splitlines()
        if not line.startswith(" ")
    }

    return lockfile


def resolve_dependencies(graphs: Iterable[MultiDiGraph]) -> Mapping[str, Set[str]]:
    dependencies = {}

    for graph in graphs:
        for node in graph:
            if node not in dependencies:
                dependencies[node] = {edge[1] for edge in graph.out_edges(node)}

    return dependencies


async def resolve(
    settings: Settings,
    state: None,
    options: Options,
    requirements_list: AsyncIterable[AsyncIterable[str]],
    locks: AsyncIterable[Lock],
) -> AsyncIterable[ResolutionGraph]:
    logger.info(f"Resolve begin, options: {options}")

    database_path, _ = get_cache_paths(settings.cache_path)

    if not database_path.exists():
        stderr.write("arch: Creating database...\n")
        await update_database(settings, state)
        stderr.write("arch: Created database.\n")

    async with TaskGroup() as group:
        tasks_list = [
            [
                group.create_task(resolve_requirement(database_path, requirement))
                async for requirement in requirements
            ]
            async for requirements in requirements_list
        ]

    graphs_list = [[task.result() for task in tasks] for tasks in tasks_list]

    roots = [[root for _, root in graphs] for graphs in graphs_list]

    versions = await resolve_versions(
        database_path,
        {package for graphs in graphs_list for graph, _ in graphs for package in graph},
    )

    async for lock in locks:
        version = versions.get(lock.name)
        if version is not None and version != lock.version:
            return

    dependencies = resolve_dependencies(
        graph for graphs in graphs_list for graph, _ in graphs
    )

    yield ResolutionGraph(
        roots,
        [
            ResolutionGraphNode(
                package_name,
                versions[package_name],
                dependencies[package_name],
                [],
            )
            for package_name in versions
        ],
    )
