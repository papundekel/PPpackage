from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable, Mapping, Set
from pathlib import Path

from networkx import MultiDiGraph, nx_pydot
from PPpackage_utils.parse import ResolutionGraph, ResolutionGraphNode, ResolveInput
from PPpackage_utils.utils import MyException, asubprocess_communicate, frozendict
from pydot import graph_from_dot_data

from .update_database import update_database
from .utils import get_cache_paths


async def resolve_pactree(
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
        stderr=None,
    )

    graph_bytes = await asubprocess_communicate(process, "Error in `pactree`.")

    graph_string = graph_bytes.decode("ascii")

    dot = graph_from_dot_data(graph_string)

    if dot is None:
        raise MyException("Error in `pactree`. Output is not a graph.")

    graph: MultiDiGraph = nx_pydot.from_pydot(dot[0])

    root = clean_graph(graph)

    return graph, root


def get_graph_root(graph: MultiDiGraph) -> str:
    for edge in graph.out_edges("START"):
        return edge[1]

    raise MyException("Error in `pactree`. Graph has no root.")


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
    database_path: Path, packages: Set[str]
) -> Mapping[str, str]:
    process = create_subprocess_exec(
        "pacinfo",
        "--dbpath",
        str(database_path),
        "--short",
        *packages,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(await process, "Error in `pacinfo`.")

    lockfile = frozendict(
        {
            (split_line := line.split())[0]
            .split("/")[-1]: split_line[1]
            .rsplit("-", 1)[0]
            for line in stdout.decode("ascii").splitlines()
            if not line.startswith(" ")
        }
    )

    return lockfile


def resolve_dependencies(graphs: Iterable[MultiDiGraph]) -> Mapping[str, Set[str]]:
    dependencies = {}

    for graph in graphs:
        for node in graph:
            if node not in dependencies:
                dependencies[node] = frozenset(
                    [edge[1] for edge in graph.out_edges(node)]
                )

    return dependencies


async def resolve(cache_path: Path, input: ResolveInput[str]) -> Set[ResolutionGraph]:
    database_path, _ = get_cache_paths(cache_path)

    if not database_path.exists():
        await update_database(cache_path)

    async with TaskGroup() as group:
        tasks_list = [
            {
                group.create_task(resolve_pactree(database_path, requirement))
                for requirement in requirements
            }
            for requirements in input.requirements_list
        ]

    graphs_list = [{task.result() for task in tasks} for tasks in tasks_list]

    roots = tuple(frozenset([root for _, root in graphs]) for graphs in graphs_list)

    versions_task = resolve_versions(
        database_path,
        {package for graphs in graphs_list for graph, _ in graphs for package in graph},
    )

    dependencies = resolve_dependencies(
        graph for graphs in graphs_list for graph, _ in graphs
    )

    versions = await versions_task

    return frozenset(
        [
            ResolutionGraph(
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
        ]
    )
