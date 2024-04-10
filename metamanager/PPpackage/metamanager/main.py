from collections.abc import AsyncIterable, Iterable, Set
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from typing import IO

from asyncstdlib import max as async_max
from networkx import MultiDiGraph
from pydantic import ValidationError

from PPpackage.utils.validation import load_from_bytes

from .exceptions import SubmanagerCommandFailure
from .repositories import Repositories
from .resolve import resolve
from .schemes import Config, Input
from .translators import Translators

logger = getLogger(__name__)


def log_exception(e: BaseExceptionGroup) -> None:
    for e in e.exceptions:
        if isinstance(e, ExceptionGroup):
            log_exception(e)
        else:
            stderr.write(f"ERROR: {e.message}\n")


def parse_input(stdin: IO[bytes]) -> Input:
    input_json_bytes = stdin.read()

    try:
        input = load_from_bytes(Input, memoryview(input_json_bytes))
    except ValidationError as e:
        stderr.write("ERROR: Invalid input.\n")
        stderr.write(e.json(indent=4))

        raise

    return input


def parse_config(config_path: Path) -> Config:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = load_from_bytes(Config, memoryview(config_json_bytes))
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


def build_graph(model: Set[str]) -> MultiDiGraph:
    return MultiDiGraph()  # TODO


async def select_best_model(models: AsyncIterable[Set[str]]) -> Set[str]:
    model_result = await async_max(
        (sorted(model) async for model in models), default=None
    )

    if model_result is None:
        raise SubmanagerCommandFailure("No model found.")

    return set(model_result)


def graph_to_dot(graph: MultiDiGraph, path: Path) -> None:
    # TODO
    pass


async def main(
    workdir_path: Path,
    config_path: Path,
    destination_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
) -> None:
    config = parse_config(config_path)

    translators = Translators(config.requirement_translators)

    async with Repositories(
        config.repository_drivers, config.repositories
    ) as repositories:
        input = parse_input(stdin.buffer)

        try:
            models = resolve(
                repositories, translators, input.requirements, input.options
            )

            model = await select_best_model(models)

            print(model, file=stderr)

            graph = build_graph(model)

            if graph_path is not None:
                graph_to_dot(graph, graph_path)

            # TODO fetch, install, generate

            stderr.write("Done.\n")

        except* SubmanagerCommandFailure as e_group:
            log_exception(e_group)
            stderr.write("Aborting.\n")
