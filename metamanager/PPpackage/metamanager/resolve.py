from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
    Awaitable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
    Set,
)
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import Requirement

from metamanager.PPpackage.metamanager.exceptions import NoModelException
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.utils import Result, TemporaryDirectory

from .build_formula import build_formula
from .repository import Repository
from .translate_options import translate_options
from .translators import Translator


def get_variable_int(
    mapping_to_int: MutableMapping[str, int],
    mapping_to_string: MutableSequence[str],
    variable: str,
) -> int:
    value = mapping_to_int.get(variable)

    if value is None:
        value = len(mapping_to_string) + 1
        mapping_to_int[variable] = value
        mapping_to_string.append(variable)

    return value


async def save_to_dimacs(
    formula: AsyncIterable[list[Literal]], path: Path
) -> tuple[Mapping[str, int], Sequence[str]]:
    mapping_to_int = dict[str, int]()
    mapping_to_string = list[str]()
    clause_count = 0

    formula_mapped = list[list[int]]()

    async for clause in formula:
        clause_mapped = list[int]()

        for literal in clause:
            symbol_mapped = get_variable_int(
                mapping_to_int, mapping_to_string, literal.symbol
            )
            clause_mapped.append(symbol_mapped if literal.polarity else -symbol_mapped)

        if len(clause_mapped) == 0:
            raise NoModelException

        formula_mapped.append(clause_mapped)

        clause_count += 1

    with path.open("w") as file:
        file.write(f"p cnf {len(mapping_to_string)} {clause_count}\n")

        for clause in formula_mapped:
            for literal in clause:
                file.write(f"{literal} ")
            file.write("0\n")

    return mapping_to_int, mapping_to_string


def save_assumptions(
    mapping_to_int: Mapping[str, int], assumptions: Iterable[Literal], path: Path
):
    with path.open("w") as file:
        for assumption in assumptions:
            assumption_integer = mapping_to_int.get(assumption.symbol)

            if assumption_integer is not None:
                file.write(
                    f"{'' if assumption.polarity else '-'}{assumption_integer}\n"
                )


async def solve(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    formula: AsyncIterable[list[Literal]],
) -> Set[str]:
    containerizer_workdir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(containerizer_workdir) as mount_dir_path:
        formula_path = mount_dir_path / "formula"
        assumptions_path = mount_dir_path / "assumptions"
        output_path = mount_dir_path / "output"

        mapping_to_int, mapping_to_string = await save_to_dimacs(formula, formula_path)

        _, assumptions = await translators_task

        save_assumptions(mapping_to_int, assumptions, assumptions_path)

        return_code = containerizer.run(
            [],
            image="docker.io/fackop/pppackage-solver:latest",
            mounts=[
                {
                    "type": "bind",
                    "source": str(containerizer.translate(mount_dir_path)),
                    "target": "/mnt/",
                }
            ],
        )

        if return_code != 0:
            raise Exception("Failed to solve")

        with output_path.open("r") as file:
            return {
                mapping_to_string[int(variable_int) - 1]
                for variable_int in file.readlines()
            }


async def resolve(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    repositories: Iterable[Repository],
    translators_task: Awaitable[tuple[Mapping[str, Translator], Iterable[Literal]]],
    options: Any,
    requirements: Iterable[Requirement],
) -> tuple[Mapping[Repository, Any], Set[str]]:

    async with TaskGroup() as task_group:
        repository_with_translated_options_tasks = translate_options(
            task_group, repositories, options
        )

        repository_to_translated_options_result = Result[Mapping[Repository, Any]]()

        formula = build_formula(
            repository_with_translated_options_tasks,
            translators_task,
            requirements,
            repository_to_translated_options_result,
        )

        model = await solve(
            containerizer, containerizer_workdir, translators_task, formula
        )

    return repository_to_translated_options_result.get(), model
