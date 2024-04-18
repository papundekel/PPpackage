from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSet,
    Sequence,
    Set,
)
from itertools import chain
from sys import stderr
from typing import Any
from typing import cast as type_cast

from asyncstdlib import chain as async_chain
from asyncstdlib import islice as async_islice
from asyncstdlib import min as async_min
from asyncstdlib import sync as make_async
from networkx import MultiDiGraph
from PPpackage.repository_driver.interface.schemes import Requirement, SimpleRequirement
from PPpackage.repository_driver.interface.utils import (
    RequirementVisitor,
    visit_requirements,
)
from pysat.formula import And, Atom, Equals, Formula, Implies, Neg, Or, XOr
from pysat.solvers import Solver

from metamanager.PPpackage.metamanager.exceptions import SubmanagerCommandFailure

from .repository import Repository
from .translators import Translator


async def repository_discover_packages(
    repository: Repository,
    packages_to_repositories_and_groups: MutableMapping[
        str, tuple[Repository, Set[str]]
    ],
):
    async for package in repository.discover_packages():
        packages_to_repositories_and_groups[package.package] = (
            repository,
            package.translator_groups,
        )


async def discover_packages(
    repositories: Iterable[Repository],
) -> Mapping[str, tuple[Repository, Set[str]]]:
    packages_to_repositories_and_groups = dict[str, tuple[Repository, Set[str]]]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(
                repository_discover_packages(
                    repository, packages_to_repositories_and_groups
                )
            )

    return packages_to_repositories_and_groups


async def get_formula(
    repositories: Iterable[Repository], options: Any
) -> AsyncIterable[Requirement]:
    for repository in repositories:
        async for requirement in repository.translate_options_and_get_formula(options):
            yield requirement


def group_packages(packages: Mapping[str, tuple[Repository, Set[str]]]):
    grouped_packages = dict[str, MutableSet[str]]()

    for package, (_, translator_groups) in packages.items():
        for translator_group in translator_groups:
            grouped_packages.setdefault(translator_group, set()).add(package)

    return grouped_packages


async def translate_requirements(
    translators: Mapping[str, Translator],
    packages: Mapping[str, tuple[Repository, Set[str]]],
    formula: AsyncIterable[Requirement],
) -> Formula:
    grouped_packages = group_packages(packages)

    async def simple_visitor(r: SimpleRequirement):
        if r.translator == "noop":
            return Atom(r.value)

        return await translators[r.translator].translate_requirement(
            grouped_packages, r.value
        )

    async with TaskGroup() as group:
        tasks = [
            group.create_task(
                visit_requirements(
                    requirement,
                    RequirementVisitor(
                        simple_visitor=simple_visitor,
                        negated_visitor=make_async(Neg),
                        and_visitor=make_async(lambda x: And(*x, merge=True)),
                        or_visitor=make_async(lambda x: Or(*x, merge=True)),
                        xor_visitor=make_async(lambda x: XOr(*x, merge=True)),
                        implication_visitor=make_async(Implies),
                        equivalence_visitor=make_async(
                            lambda x: Equals(*x, merge=True)
                        ),
                    ),
                )
            )
            async for requirement in formula
        ]

    return And(*(task.result() for task in tasks), merge=True)


def generate_smaller_models(
    model: Sequence[Atom | Neg],
) -> Iterable[Sequence[Atom | Neg]]:
    for i in range(len(model)):
        literal = model[i]
        if isinstance(literal, Atom):
            yield list(
                chain(
                    model[:i],
                    [type_cast(Neg, Neg(literal))],
                    model[i + 1 :],
                )
            )


def minimize_model(
    formula: Formula, model: Sequence[Atom | Neg]
) -> Sequence[Atom | Neg]:
    while True:
        smaller_model = next(
            (x for x in generate_smaller_models(model) if formula.satisfied(x)),
            None,
        )

        if smaller_model is None:
            break

        model = smaller_model

    return model


def process_model(packages: Set[str], model: Sequence[Atom | Neg]) -> Set[str]:
    set_variables = {
        type_cast(str, atom.object) for atom in model if isinstance(atom, Atom)
    }

    return packages & set_variables


async def enumerate_models(packages: Set[str], formula: Formula):
    with Solver(bootstrap_with=formula, name="glucose421") as solver:
        for model_integers in solver.enum_models():  # type: ignore
            model_atoms = Formula.formulas(model_integers, atoms_only=True)

            # minimized_model_atoms = minimize_model(formula, model_atoms)
            minimized_model_atoms = model_atoms

            yield process_model(packages, minimized_model_atoms)


async def select_best_model(
    models: AsyncIterable[Set[str]],
    packages_to_repositories: Mapping[str, tuple[Repository, Set[str]]],
) -> MultiDiGraph:
    # from models with the fewest packages
    # select the lexicographically smallest
    model_result: list[str] | None = await async_min(
        (sorted(model) async for model in async_islice(models, None, 1)),  # type: ignore
        key=lambda x: (len(x), x),  # type: ignore
        default=None,
    )

    if model_result is None:
        raise SubmanagerCommandFailure("No model found.")

    graph = MultiDiGraph()

    graph.add_nodes_from(
        (package, {"repository": packages_to_repositories[package][0]})
        for package in model_result
    )

    return graph


async def resolve(
    repositories: Iterable[Repository],
    translators: Mapping[str, Translator],
    requirements: Requirement,
    options: Any,
) -> MultiDiGraph:
    stderr.write("Translating requirements...\n")

    packages_to_repositories_and_groups = await discover_packages(repositories)
    packages = packages_to_repositories_and_groups.keys()
    formula = get_formula(repositories, options)

    translated_formula = await translate_requirements(
        translators,
        packages_to_repositories_and_groups,
        async_chain([requirements], formula),
    )

    stderr.write("Resolving...\n")

    models = enumerate_models(packages, translated_formula)

    graph = await select_best_model(models, packages_to_repositories_and_groups)

    return graph
