from asyncio import as_completed
from collections.abc import AsyncIterable, Awaitable, Iterable, Mapping
from itertools import chain, product
from re import L
from sys import stderr
from typing import Any

from asyncstdlib import chain as async_chain

from PPpackage.repository_driver.interface.schemes import Requirement
from PPpackage.utils.utils import Result

from .repository import Repository
from .schemes import Literal
from .translators import Translator


async def get_formula(
    repositories_with_translated_options_tasks: Iterable[
        Awaitable[tuple[Repository, Any]]
    ],
    repositories_to_translated_options_result: Result[Mapping[Repository, Any]],
) -> AsyncIterable[list[Requirement]]:
    repositories_to_translated_options = dict[Repository, Any]()

    for translated_options_task in as_completed(
        repositories_with_translated_options_tasks
    ):
        repository, translated_options = await translated_options_task
        async for requirement in repository.get_formula(translated_options):
            yield requirement

        repositories_to_translated_options[repository] = translated_options

    repositories_to_translated_options_result.set(repositories_to_translated_options)


def translate_requirement(
    translators: Mapping[str, Translator], requirement: Requirement
) -> Iterable[str]:
    translator_name = requirement.translator

    if translator_name == "noop":
        return [requirement.value]

    translator = translators[translator_name]

    translated_requirement = translator.translate_requirement(requirement.value)

    return translated_requirement


async def translate_requirements(
    translators: Mapping[str, Translator],
    formula: AsyncIterable[list[Requirement]],
) -> AsyncIterable[list[Literal]]:
    async for clause in formula:
        positive_buffer = list[Literal]()
        negative_buffer = list[list[str]]()

        for literal in clause:
            translated_requirement = translate_requirement(translators, literal)

            if literal.polarity:
                positive_buffer.extend(
                    Literal(symbol, True) for symbol in translated_requirement
                )
            else:
                negative_buffer.append(list(translated_requirement))

        for combination in product(*negative_buffer):
            translated_clause = list(
                chain(
                    positive_buffer,
                    (Literal(symbol, False) for symbol in combination),
                )
            )

            yield translated_clause


async def build_formula(
    repository_with_translated_options_tasks: Iterable[
        Awaitable[tuple[Repository, Any]]
    ],
    translators_task: Awaitable[Mapping[str, Translator]],
    requirements: Iterable[Requirement],
    repository_to_translated_options_result: Result[Mapping[Repository, Any]],
) -> AsyncIterable[list[Literal]]:
    stderr.write("Fetching translator data and translating options...\n")

    formula = get_formula(
        repository_with_translated_options_tasks,
        repository_to_translated_options_result,
    )

    stderr.write("Fetching formula and translating requirements...\n")

    async for clause in translate_requirements(
        await translators_task,
        async_chain(([requirement] for requirement in requirements), formula),
    ):
        yield clause
