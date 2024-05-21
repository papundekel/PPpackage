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
from typing import Any

from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import Requirement

from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.utils import Result, TemporaryDirectory

from .build_formula import build_formula
from .exceptions import NoModelException
from .repository import Repository
from .translate_options import translate_options
from .translators import Translator


def get_variable_mapping(
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


async def map_formula(
    formula: AsyncIterable[list[Literal]],
) -> tuple[Sequence[list[int]], Mapping[str, int], Sequence[str]]:
    mapping_to_int = dict[str, int]()
    mapping_to_string = list[str]()

    mapped_formula = list[list[int]]()

    async for clause in formula:
        mapped_clause = list[int]()

        for literal in clause:
            symbol_mapped = get_variable_mapping(
                mapping_to_int, mapping_to_string, literal.symbol
            )
            mapped_clause.append(symbol_mapped if literal.polarity else -symbol_mapped)

        if len(mapped_clause) == 0:
            raise NoModelException

        mapped_formula.append(mapped_clause)

    return mapped_formula, mapping_to_int, mapping_to_string


def write_dimacs(formula: Sequence[list[int]], variable_count: int, path: Path):
    with path.open("w") as file:
        file.write(f"p cnf {variable_count} {len(formula)}\n")

        for clause in formula:
            for literal in clause:
                file.write(f"{literal} ")
            file.write("0\n")


async def save_to_dimacs(
    formula: AsyncIterable[list[Literal]], path: Path
) -> tuple[Mapping[str, int], Sequence[str]]:
    mapped_formula, mapping_to_int, mapping_to_string = await map_formula(formula)

    write_dimacs(mapped_formula, len(mapping_to_string), path)

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
            if return_code == 1:
                raise NoModelException
            else:
                raise Exception("Error in solver.")

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

        requirements = list(requirements)

        formula = build_formula(
            repository_with_translated_options_tasks,
            translators_task,
            requirements,
            repository_to_translated_options_result,
        )

        try:
            model = await solve(
                containerizer, containerizer_workdir, translators_task, formula
            )
        except NoModelException:
            raise NoModelException(requirements)

    return repository_to_translated_options_result.get(), model
