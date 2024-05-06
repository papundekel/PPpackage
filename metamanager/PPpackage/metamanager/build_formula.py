from asyncio import TaskGroup, as_completed
from collections.abc import AsyncIterable, Awaitable, Iterable, Mapping
from sys import stderr
from typing import Any

from asyncstdlib import chain as async_chain
from asyncstdlib import sync as make_async
from PPpackage.repository_driver.interface.schemes import Requirement, SimpleRequirement
from PPpackage.repository_driver.interface.utils import (
    RequirementVisitor,
    visit_requirements,
)
from pysat.formula import And, Atom, Equals, Formula, Implies, Neg, Or, XOr

from PPpackage.utils.utils import Result

from .repository import Repository
from .translators import Translator


async def get_formula(
    repositories_with_translated_options_tasks: Iterable[
        Awaitable[tuple[Repository, Any]]
    ],
    repositories_to_translated_options_result: Result[Mapping[Repository, Any]],
) -> AsyncIterable[Requirement]:
    repositories_to_translated_options = dict[Repository, Any]()

    for translated_options_task in as_completed(
        repositories_with_translated_options_tasks
    ):
        repository, translated_options = await translated_options_task
        async for requirement in repository.get_formula(translated_options):
            yield requirement

        repositories_to_translated_options[repository] = translated_options

    repositories_to_translated_options_result.set(repositories_to_translated_options)


async def translate_requirements(
    translators: Mapping[str, Translator], formula: AsyncIterable[Requirement]
) -> Formula:
    async def simple_visitor(r: SimpleRequirement):
        if r.translator == "noop":
            return Atom(r.value)

        return await translators[r.translator].translate_requirement(r.value)

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


async def build_formula(
    repository_with_translated_options_tasks: Iterable[
        Awaitable[tuple[Repository, Any]]
    ],
    translators_task: Awaitable[Mapping[str, Translator]],
    requirement: Requirement,
) -> tuple[Mapping[Repository, Any], Formula]:
    stderr.write("Fetching translator data and translating options...\n")

    repository_to_translated_options_result = Result[Mapping[Repository, Any]]()

    formula = get_formula(
        repository_with_translated_options_tasks,
        repository_to_translated_options_result,
    )

    stderr.write("Fetching formula and translating requirements...\n")

    translated_formula = await translate_requirements(
        await translators_task, async_chain([requirement], formula)
    )

    repository_to_translated_options = repository_to_translated_options_result.get()

    return repository_to_translated_options, translated_formula
