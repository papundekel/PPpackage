from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
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

from .repository import Repository
from .translators import Translator


async def repository_fetch_packages(
    repository: Repository, packages: MutableMapping[str, Set[str]]
):
    async for package in repository.fetch_packages():
        packages[package.package] = package.translator_groups


async def fetch_packages(
    repositories: Iterable[Repository],
) -> Mapping[str, Set[str]]:
    packages = dict[str, Set[str]]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(repository_fetch_packages(repository, packages))

    return packages


async def fetch_formula(
    repositories: Iterable[Repository], options: Any
) -> Iterable[Requirement]:
    formula = list[Requirement]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(
                repository.translate_options_and_fetch_formula(options, formula)
            )

    return formula


async def fetch_packages_and_formulas(
    repositories: Iterable[Repository], options: Any
) -> tuple[Mapping[str, Set[str]], Iterable[Requirement]]:
    async with TaskGroup() as group:
        packages_task = group.create_task(fetch_packages(repositories))
        formula_task = group.create_task(fetch_formula(repositories, options))

    return packages_task.result(), formula_task.result()


def group_packages(packages: Mapping[str, Set[str]]):
    grouped_packages = dict[str, MutableSet[str]]()

    for package, translator_groups in packages.items():
        for translator_group in translator_groups:
            grouped_packages.setdefault(translator_group, set()).add(package)

    return grouped_packages


def translate_requirements(
    translators: Mapping[str, Translator],
    packages: Mapping[str, Set[str]],
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
) -> AsyncIterable[Set[str]]:
    stderr.write("Resolving requirements:\n")

    # TODO: better print
    print(requirements, file=stderr)

    stderr.write("Fetching packages and formulas...\n")

    packages_with_groups, formula = await fetch_packages_and_formulas(
        repositories, options
    )

    stderr.write("Packages and formulas fetched.\n")

    stderr.write("Translating requirements...\n")

    translated_formula = translate_requirements(
        translators, packages_with_groups, chain([requirements], formula)
    )

    stderr.write("Requirements translated.\n")

    print(translated_formula, file=stderr)

    stderr.write("Resolving...\n")

    packages = packages_with_groups.keys()

    with Solver(name="glucose42", bootstrap_with=translated_formula) as solver:
        for model_integers in solver.enum_models():  # type: ignore
            model_atoms = Formula.formulas(model_integers, atoms_only=True)

            model = process_model(packages, model_atoms)

            yield model

    stderr.write("Resolution done.\n")
