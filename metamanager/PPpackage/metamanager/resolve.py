from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
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
from pysat.formula import And, Atom, Equals, Formula, Implies, Neg, Or, XOr
from pysat.solvers import Solver

from PPpackage.repository_driver.interface.schemes import Requirement, SimpleRequirement
from PPpackage.repository_driver.interface.utils import (
    RequirementVisitor,
    visit_requirements,
)

from .exceptions import SubmanagerCommandFailure
from .repository import Repository
from .translators import Translator


async def repository_fetch_translator_data(
    repository: Repository,
    translator_info: MutableMapping[str, MutableSequence[dict[str, str]]],
):
    async for info in repository.fetch_translator_data():
        translator_info.setdefault(info.group, []).append(info.symbol)


async def fetch_translator_data(
    repositories: Iterable[Repository],
) -> Mapping[str, Iterable[dict[str, str]]]:
    translator_info = dict[str, MutableSequence[dict[str, str]]]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(
                repository_fetch_translator_data(repository, translator_info)
            )

    return translator_info


async def translate_options(
    repositories: Iterable[Repository],
    options: Any,
) -> None:
    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(repository.translate_options(options))


async def get_formula(repositories: Iterable[Repository]) -> AsyncIterable[Requirement]:
    for repository in repositories:
        async for requirement in repository.get_formula():
            yield requirement


async def translate_requirements(
    translators: Mapping[str, Translator],
    translator_data: Mapping[str, Iterable[dict[str, str]]],
    formula: AsyncIterable[Requirement],
) -> Formula:
    async def simple_visitor(r: SimpleRequirement):
        if r.translator == "noop":
            return Atom(r.value)

        return await translators[r.translator].translate_requirement(
            translator_data, r.value
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


async def enumerate_models(formula: Formula):
    with Solver(bootstrap_with=formula, name="glucose421") as solver:
        for model_integers in solver.enum_models():  # type: ignore
            model_atoms = Formula.formulas(model_integers, atoms_only=True)

            # minimized_model_atoms = minimize_model(formula, model_atoms)
            minimized_model_atoms = model_atoms

            yield {
                type_cast(str, atom.object)
                for atom in minimized_model_atoms
                if isinstance(atom, Atom)
            }


async def select_best_model(
    models: AsyncIterable[Set[str]],
) -> Set[str]:
    # from models with the fewest packages
    # select the lexicographically smallest
    model_result: list[str] | None = await async_min(
        (sorted(model) async for model in async_islice(models, None, 1)),  # type: ignore
        key=lambda x: (len(x), x) if x is not None else None,  # type: ignore
        default=None,
    )

    if model_result is None:
        raise SubmanagerCommandFailure("No model found.")

    return set(model_result)


def create_graph(model: Set[str]):
    graph = MultiDiGraph()

    graph.add_nodes_from(model)

    return graph


async def resolve(
    repositories: Iterable[Repository],
    translators: Mapping[str, Translator],
    requirements: Requirement,
    options: Any,
) -> Set[str]:
    stderr.write("Fetching translator data and translating options...\n")

    async with TaskGroup() as group:
        translator_data_task = group.create_task(fetch_translator_data(repositories))
        group.create_task(translate_options(repositories, options))

    formula = get_formula(repositories)

    stderr.write("Fetching formula and translating requirements...\n")

    translated_formula = await translate_requirements(
        translators, translator_data_task.result(), async_chain([requirements], formula)
    )

    stderr.write("Resolving...\n")

    models = enumerate_models(translated_formula)

    return await select_best_model(models)
