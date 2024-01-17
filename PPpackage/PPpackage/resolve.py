from asyncio import TaskGroup
from collections.abc import (
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Set,
)
from dataclasses import dataclass
from itertools import product as itertools_product
from json import dumps as json_dumps
from sys import stderr
from typing import Any

from frozendict import frozendict
from networkx import MultiDiGraph, is_directed_acyclic_graph
from PPpackage_submanager.schemes import (
    ManagerAndName,
    ManagerRequirement,
    Options,
    ResolutionGraph,
)

from PPpackage.submanager import Submanager

from .utils import SubmanagerCommandFailure


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
    requirements_list: Iterable[Set[Hashable]], resolution_graph: ResolutionGraph
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


async def resolve_manager(
    submanager: Submanager,
    options: Options,
    requirements_list: Iterable[Set[Hashable]],
    resolution_graphs: Mapping[str, MutableSequence[ResolutionGraph]],
):
    async for resolution_graph in submanager.resolve(options, requirements_list):
        resolution_graphs[submanager.name].append(resolution_graph)


async def resolve_iteration(
    submanagers: Mapping[str, Submanager],
    meta_options: Mapping[str, Any],
    requirements: Mapping[str, Set[Set[Hashable]]],
    initial: Mapping[str, Set[Hashable]],
    new_choices: MutableSequence[Any],
    results: MutableSequence[Mapping[str, WorkGraph]],
) -> None:
    requirements_lists = dict[str, Iterable[Set[Hashable]]]()

    for submanager_name, requirements_set in requirements.items():
        requirements_lists[submanager_name] = list(requirements_set)

    resolution_graphs = dict[str, MutableSequence[ResolutionGraph]]()

    async with TaskGroup() as group:
        for submanager_name, requirements_list in requirements_lists.items():
            resolution_graphs[submanager_name] = []
            submanager = submanagers[submanager_name]

            group.create_task(
                resolve_manager(
                    submanager,
                    meta_options.get(submanager.name),
                    requirements_list,
                    resolution_graphs,
                )
            )

    for managers_and_graphs in itertools_product(
        *[
            [(manager, graph) for graph in graphs]
            for manager, graphs in resolution_graphs.items()
        ]
    ):
        meta_graph = {
            manager: make_graph(requirements_lists[manager], graph)
            for manager, graph in managers_and_graphs
        }

        resolved_requirements = get_resolved_requirements(meta_graph)
        all_requirements = merge_requirements(initial, get_all_requirements(meta_graph))

        if resolved_requirements == all_requirements:
            results.append(meta_graph)
        else:
            new_choices.append(all_requirements)


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


def process_graph(manager_work_graph: Mapping[str, WorkGraph]) -> MultiDiGraph:
    graph = MultiDiGraph()

    graph.add_nodes_from(
        (ManagerAndName(manager, package_name), {"version": value.version})
        for manager, work_graph in manager_work_graph.items()
        for package_name, value in work_graph.graph.items()
    )

    graph.add_edges_from(
        {
            (
                ManagerAndName(manager, package_name),
                ManagerAndName(manager, dependency_name),
            )
            for manager, work_graph in manager_work_graph.items()
            for package_name, value in work_graph.graph.items()
            for dependency_name in value.dependencies
        }
        | {
            (
                ManagerAndName(manager, package_name),
                ManagerAndName(requirement_manager, dependency_name),
            )
            for manager, work_graph in manager_work_graph.items()
            for package_name, value in work_graph.graph.items()
            for requirement_manager, requirement in value.requirements.items()
            for dependency_name in manager_work_graph[requirement_manager].roots[
                requirement
            ]
        }
    )

    return graph


async def resolve(
    submanagers: Mapping[str, Submanager],
    iteration_limit: int,
    initial_requirements: Mapping[str, Set[Any]],
    meta_options: Mapping[str, Any],
) -> MultiDiGraph:
    stderr.write("Resolving requirements...\n")

    for manager, requirements in sorted(
        initial_requirements.items(), key=lambda x: x[0]
    ):
        stderr.write(f"{manager}:\n")
        for requirement in requirements:
            stderr.write(f"\t{json_dumps(requirement)}\n")

    iterations_done = 0

    all_requirements_choices = [
        {
            manager: frozenset([requirements])
            for manager, requirements in initial_requirements.items()
        }
    ]

    results_work_graph: MutableSequence[Mapping[str, WorkGraph]] = []

    while True:
        stderr.write(f"Resolution iteration {iterations_done + 1}...\n")

        if iterations_done >= iteration_limit:
            raise SubmanagerCommandFailure("Resolve iteration limit reached.")

        new_choices = []

        async with TaskGroup() as group:
            for all_requirements in all_requirements_choices:
                group.create_task(
                    resolve_iteration(
                        submanagers,
                        meta_options,
                        all_requirements,
                        initial_requirements,
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

    stderr.write("Resolution done.\n")

    for manager, work_graph in sorted(result_work_graph.items(), key=lambda x: x[0]):
        stderr.write(f"{manager}:\n")
        for package_name, value in sorted(work_graph.graph.items(), key=lambda x: x[0]):
            stderr.write(f"\t{package_name} -> {value.version}\n")

    graph = process_graph(result_work_graph)

    if not is_directed_acyclic_graph(graph):
        raise SubmanagerCommandFailure("Cycle found in the resolution graph.")

    return graph
