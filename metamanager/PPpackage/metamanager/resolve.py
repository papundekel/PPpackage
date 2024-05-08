from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
    Awaitable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Set,
)
from pathlib import Path
from sys import stderr
from typing import Any

from metamanager.PPpackage.metamanager.exceptions import NoModelException
from PPpackage.container_utils import Containerizer
from PPpackage.repository_driver.interface.schemes import Requirement
from PPpackage.utils.utils import Result, TemporaryDirectory

from .build_formula import build_formula
from .repository import Repository
from .schemes import Literal
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
) -> list[str]:
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

    return mapping_to_string


async def solve(
    containerizer: Containerizer,
    containerizer_workdir: Path,
    formula: AsyncIterable[list[Literal]],
) -> Set[str]:
    with TemporaryDirectory(containerizer_workdir) as mount_dir_path:
        formula_path = mount_dir_path / "input"
        output_path = mount_dir_path / "output"

        mapping_to_string = await save_to_dimacs(formula, formula_path)

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
    translators_task: Awaitable[Mapping[str, Translator]],
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

        stderr.write("Resolving...\n")

        model = await solve(containerizer, containerizer_workdir, formula)

    return repository_to_translated_options_result.get(), model
