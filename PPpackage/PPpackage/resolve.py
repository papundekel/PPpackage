from asyncio import Task, TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import (
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
)
from dataclasses import dataclass
from functools import partial
from itertools import product as itertools_product
from pathlib import Path
from typing import Any

from frozendict import frozendict
from networkx import MultiDiGraph, is_directed_acyclic_graph
from PPpackage_utils.parse import (
    ManagerRequirement,
    Options,
    ResolutionGraph,
    ResolveInput,
    dump_one,
    load_one,
)
from PPpackage_utils.utils import MyException, asubprocess_wait

from .sub import resolve as PP_resolve


async def resolve_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    options: Options,
    requirements_list: Iterable[Iterable[Any]],
) -> Iterable[ResolutionGraph]:
    process = await create_subprocess_exec(
        f"PPpackage-{manager}",
        "--debug" if debug else "--no-debug",
        "resolve",
        str(cache_path),
        stdin=PIPE,
        stdout=PIPE,
        stderr=None,
    )

    assert process.stdin is not None
    assert process.stdout is not None

    input_task = dump_one(
        debug,
        process.stdin,
        ResolveInput[Any](options=options, requirements_list=requirements_list),
    )

    output_task = load_one(debug, process.stdout, Iterable[ResolutionGraph])

    await input_task
    await asubprocess_wait(process, f"Error in {manager}'s resolve.")

    return await output_task


async def resolve_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    options: Options,
    requirements_list: Iterable[Iterable[Any]],
) -> Iterable[ResolutionGraph]:
    if manager == "PP":
        resolver = PP_resolve
    else:
        resolver = partial(resolve_external_manager, manager=manager)

    resolutions = await resolver(
        debug=debug,
        cache_path=cache_path,
        options=options,
        requirements_list=requirements_list,
    )

    return resolutions


@dataclass(frozen=True)
class WorkGraphNodeValue:
    version: str
    dependencies: Set[str]
    requirements: Mapping[str, frozenset[Any]]


@dataclass(frozen=True)
class WorkGraph:
    roots: Mapping[frozenset[Hashable], Set[str]]
    graph: Mapping[str, WorkGraphNodeValue]


def get_resolved_requirements(
    meta_graph: Mapping[str, WorkGraph]
) -> Mapping[str, Set[Set[Hashable]]]:
    return {
        manager: {requirements for requirements in graph.roots.keys()}
        for manager, graph in meta_graph.items()
    }


def get_all_requirements(
    meta_graph: Mapping[str, WorkGraph]
) -> Mapping[str, Set[Set[Hashable]]]:
    all_requirements: MutableMapping[str, MutableSet[Set[Hashable]]] = {}

    for graph in meta_graph.values():
        for node_value in graph.graph.values():
            for manager_dependency, requirements in node_value.requirements.items():
                all_requirements.setdefault(manager_dependency, set()).add(requirements)

    return frozendict(all_requirements)


def process_manager_requirements(
    manager_requirements: Iterable[ManagerRequirement],
) -> Mapping[str, frozenset[Any]]:
    result: MutableMapping[str, MutableSet[Any]] = {}

    for manager_requirement in manager_requirements:
        result.setdefault(manager_requirement.manager, set()).add(
            manager_requirement.requirement
        )

    return {
        manager: frozenset(requirements) for manager, requirements in result.items()
    }


def make_graph(
    requirements_list: Sequence[Set[Hashable]], resolution_graph: ResolutionGraph
) -> WorkGraph:
    roots = frozendict(
        {
            frozenset(requirements): frozenset(roots)
            for requirements, roots in zip(requirements_list, resolution_graph.roots)
        }
    )

    graph = frozendict(
        {
            node.name: WorkGraphNodeValue(
                node.version,
                frozenset(node.dependencies),
                frozendict(process_manager_requirements(node.requirements)),
            )
            for node in resolution_graph.graph
        }
    )

    return WorkGraph(roots, graph)


async def resolve_iteration(
    debug: bool,
    cache_path: Path,
    requirements: Mapping[str, Set[Set[Hashable]]],
    meta_options: Mapping[str, Any],
) -> Iterable[Mapping[str, WorkGraph]]:
    async with TaskGroup() as group:
        lists_and_tasks = dict[
            str, tuple[Sequence[Set[Hashable]], Task[Iterable[ResolutionGraph]]]
        ]()

        for manager, requirements_set in requirements.items():
            requirements_list = list(requirements_set)
            lists_and_tasks[manager] = (
                requirements_list,
                group.create_task(
                    resolve_manager(
                        debug,
                        manager,
                        cache_path,
                        meta_options.get(manager),
                        requirements_list,
                    )
                ),
            )

    lists_and_graphs = {
        manager: (requirements_list, task.result())
        for manager, (requirements_list, task) in lists_and_tasks.items()
    }

    choices_resolution_graph = [
        {manager: (lists_and_graphs[manager][0], graph) for manager, graph in i}
        for i in itertools_product(
            *[
                [(manager, graph) for graph in graphs]
                for manager, (_, graphs) in lists_and_graphs.items()
            ]
        )
    ]

    manager_graphs = [
        {
            manager: make_graph(requirements_list, graph)
            for manager, (
                requirements_list,
                graph,
            ) in choice_resolution_graph.items()
        }
        for choice_resolution_graph in choices_resolution_graph
    ]

    return manager_graphs


def merge_requirements(initial, new):
    return frozendict(
        {
            manager: (
                (
                    frozenset([i])
                    if (i := initial.get(manager)) is not None
                    else frozenset()
                )
                | new.get(manager, frozenset())
            )
            for manager in initial.keys() | new.keys()
        }
    )


async def resolve_iteration2(
    debug: bool,
    cache_path: Path,
    initial: Mapping[str, Set[Hashable]],
    requirements: Mapping[str, Set[Set[Hashable]]],
    meta_options: Mapping[str, Any],
    new_choices: MutableSequence[Any],
    results: MutableSequence[Mapping[str, WorkGraph]],
):
    meta_graphs = await resolve_iteration(debug, cache_path, requirements, meta_options)

    for meta_graph in meta_graphs:
        resolved_requirements = get_resolved_requirements(meta_graph)
        all_requirements = merge_requirements(initial, get_all_requirements(meta_graph))

        if resolved_requirements == all_requirements:
            results.append(meta_graph)
        else:
            new_choices.append(all_requirements)


def process_graph(manager_work_graph: Mapping[str, WorkGraph]) -> MultiDiGraph:
    graph = MultiDiGraph()

    graph.add_nodes_from(
        ((manager, package), {"version": value.version})
        for manager, work_graph in manager_work_graph.items()
        for package, value in work_graph.graph.items()
    )

    graph.add_edges_from(
        {
            ((manager, package), (manager, dependency))
            for manager, work_graph in manager_work_graph.items()
            for package, value in work_graph.graph.items()
            for dependency in value.dependencies
        }
        | {
            ((manager, package), (requirement_manager, dependency))
            for manager, work_graph in manager_work_graph.items()
            for package, value in work_graph.graph.items()
            for requirement_manager, requirement in value.requirements.items()
            for dependency in manager_work_graph[requirement_manager].roots[requirement]
        }
    )

    return graph


async def resolve(
    debug: bool,
    iteration_limit: int,
    cache_path: Path,
    initial_requirements: Mapping[str, Set[Any]],
    meta_options: Mapping[str, Any],
) -> MultiDiGraph:
    iterations_done = 0

    all_requirements_choices = [
        {
            manager: frozenset([requirements])
            for manager, requirements in initial_requirements.items()
        }
    ]

    results_work_graph: MutableSequence[Mapping[str, WorkGraph]] = []

    while True:
        if iterations_done >= iteration_limit:
            raise MyException("Resolve iteration limit reached.")

        new_choices = []

        async with TaskGroup() as group:
            for all_requirements in all_requirements_choices:
                group.create_task(
                    resolve_iteration2(
                        debug,
                        cache_path,
                        initial_requirements,
                        all_requirements,
                        meta_options,
                        new_choices,
                        results_work_graph,
                    )
                )

        if len(new_choices) == 0:
            break

        all_requirements_choices = new_choices

        iterations_done += 1

    # TODO: model selection
    result_work_graph = results_work_graph.pop()

    graph = process_graph(result_work_graph)

    if not is_directed_acyclic_graph(graph):
        raise MyException("Cycle found in the resolution graph.")

    return graph
