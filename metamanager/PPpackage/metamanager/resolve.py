from asyncio import TaskGroup
from collections.abc import (
    AsyncGenerator,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSet,
    Set,
)
from itertools import chain
from sys import stderr
from typing import Any, cast

from PPpackage.repository_driver.interface.schemes import Requirement, SimpleRequirement
from PPpackage.repository_driver.interface.utils import (
    RequirementVisitor,
    visit_requirements,
)
from pysat.formula import And, Atom, Equals, Formula, Implies, Neg, Or, XOr
from pysat.solvers import Solver

from metamanager.PPpackage.metamanager.utils import Result

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
) -> Iterable[Requirement]:
    formula = list[Requirement]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(
                repository.translate_options_and_get_formula(options, formula)
            )

    return formula


async def discover_packages_and_formulas(
    repositories: Iterable[Repository], options: Any
) -> tuple[Mapping[str, tuple[Repository, Set[str]]], Iterable[Requirement]]:
    async with TaskGroup() as group:
        packages_task = group.create_task(discover_packages(repositories))
        formula_task = group.create_task(get_formula(repositories, options))

    return packages_task.result(), formula_task.result()


def group_packages(packages: Mapping[str, tuple[Repository, Set[str]]]):
    grouped_packages = dict[str, MutableSet[str]]()

    for package, (_, translator_groups) in packages.items():
        for translator_group in translator_groups:
            grouped_packages.setdefault(translator_group, set()).add(package)

    return grouped_packages


def translate_requirements(
    translators: Mapping[str, Translator],
    packages: Mapping[str, tuple[Repository, Set[str]]],
    formula: Iterable[Requirement],
) -> Formula:
    grouped_packages = group_packages(packages)

    def simple_visitor(r: SimpleRequirement):
        if r.translator == "noop":
            return Atom(r.value)

        return translators[r.translator].translate_requirement(
            grouped_packages, r.value
        )

    return And(
        *(
            visit_requirements(
                requirement,
                RequirementVisitor(
                    simple_visitor=simple_visitor,
                    negated_visitor=Neg,
                    and_visitor=lambda x: And(*x, merge=True),
                    or_visitor=lambda x: Or(*x, merge=True),
                    xor_visitor=lambda x: XOr(*x, merge=True),
                    implication_visitor=Implies,
                    equivalence_visitor=lambda x: Equals(*x, merge=True),
                ),
            )
            for requirement in formula
        ),
        merge=True
    )


def process_model(packages: Set[str], model: Iterable[Atom | Neg]) -> Set[str]:
    set_variables = {cast(str, atom.object) for atom in model if isinstance(atom, Atom)}

    return packages & set_variables


async def resolve(
    repositories: Iterable[Repository],
    translators: Mapping[str, Translator],
    requirements: Requirement,
    options: Any,
    packages_with_repositories_result: Result[
        Mapping[str, tuple[Repository, Set[str]]]
    ],
) -> AsyncGenerator[Set[str], Mapping[str, tuple[Repository, Set[str]]]]:
    stderr.write("Resolving requirements:\n")

    # TODO: better print
    print(requirements, file=stderr)

    stderr.write("Fetching packages and formulas...\n")

    packages_to_repositories_and_groups, formula = await discover_packages_and_formulas(
        repositories, options
    )
    packages_with_repositories_result.value = packages_to_repositories_and_groups

    stderr.write("Packages and formulas fetched.\n")

    stderr.write("Translating requirements...\n")

    translated_formula = translate_requirements(
        translators, packages_to_repositories_and_groups, chain([requirements], formula)
    )

    stderr.write("Requirements translated.\n")

    print(translated_formula, file=stderr)

    stderr.write("Resolving...\n")

    packages = packages_to_repositories_and_groups.keys()

    with Solver(bootstrap_with=translated_formula) as solver:
        for model_integers in solver.enum_models():  # type: ignore
            model_atoms = Formula.formulas(model_integers, atoms_only=True)

            model = process_model(packages, model_atoms)

            yield model

    stderr.write("Resolution done.\n")
