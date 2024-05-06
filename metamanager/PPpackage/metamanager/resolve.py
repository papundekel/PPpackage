from asyncio import TaskGroup
from collections.abc import Awaitable, Iterable, Mapping, Sequence, Set
from itertools import chain, islice
from sys import stderr
from typing import Any
from typing import cast as type_cast

from networkx import MultiDiGraph
from PPpackage.repository_driver.interface.schemes import Requirement
from pysat.formula import Atom, Formula, Neg
from pysat.solvers import Solver

from .build_formula import build_formula
from .exceptions import NoModelException
from .repository import Repository
from .translate_options import translate_options
from .translators import Translator


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


def enumerate_models(formula: Formula):
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


def select_best_model(
    models: Iterable[Set[str]],
) -> Set[str]:
    # from models with the fewest packages
    # select the lexicographically smallest
    model_result = min(
        (sorted(model) for model in islice(models, None, 1)),
        key=lambda x: (len(x), x),
        default=None,
    )

    if model_result is None:
        raise NoModelException

    return set(model_result)


def create_graph(model: Set[str]):
    graph = MultiDiGraph()

    graph.add_nodes_from(model)

    return graph


async def resolve(
    repositories: Iterable[Repository],
    translators_task: Awaitable[Mapping[str, Translator]],
    options: Any,
    requirement: Requirement,
) -> tuple[Mapping[Repository, Any], Set[str]]:

    async with TaskGroup() as task_group:
        repository_with_translated_options_tasks = translate_options(
            task_group, repositories, options
        )

        repository_to_translated_options, formula = await build_formula(
            repository_with_translated_options_tasks,
            translators_task,
            requirement,
        )

    stderr.write("Resolving...\n")

    models = enumerate_models(formula)

    return repository_to_translated_options, select_best_model(models)
