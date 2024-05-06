from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, Set
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from traceback import print_exc
from typing import IO, Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, convert_node_labels_to_integers
from networkx.drawing.nx_pydot import to_pydot
from PPpackage.container_utils import Containerizer
from pydantic import ValidationError
from pydot import Dot
from sqlitedict import SqliteDict

from PPpackage.utils.validation import validate_json

from .fetch_and_install import fetch_and_install
from .installer import Installers
from .repository import Repositories
from .resolve import resolve
from .schemes import Config, Input
from .translators import Translators

logger = getLogger(__name__)


def log_exception(e: BaseExceptionGroup) -> None:
    for e in e.exceptions:
        if isinstance(e, ExceptionGroup):
            log_exception(e)
        else:
            print_exc(file=stderr)


def parse_input(stdin: IO[bytes]) -> Input:
    input_json_bytes = stdin.read()

    try:
        input = validate_json(Input, input_json_bytes)
    except ValidationError as e:
        stderr.write("ERROR: Invalid input.\n")
        stderr.write(e.json(indent=4))

        raise

    return input


def parse_config(config_path: Path) -> Config:
    with config_path.open("rb") as f:
        config_json_bytes = f.read()

        try:
            config = validate_json(Config, config_json_bytes)
        except ValidationError as e:
            stderr.write("ERROR: Invalid config.\n")
            stderr.write(e.json(indent=4))

            raise

        return config


async def generators(generators_path: Path) -> None:
    # TODO
    pass


async def main(
    config_path: Path,
    installation_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
) -> None:
    config = parse_config(config_path)

    containerizer = Containerizer(config.containerizer)
    installers = Installers(config.installers)

    input = parse_input(stdin.buffer)

    try:
        async with Repositories(
            config.repository_drivers, config.repositories
        ) as repositories:
            async with TaskGroup() as task_group:
                translators_task = task_group.create_task(
                    Translators(repositories, config.requirement_translators)
                )

                repository_to_translated_options, model = await resolve(
                    repositories, translators_task, input.options, input.requirement
                )

            async with HTTPClient(http2=True) as archive_client:
                with SqliteDict(
                    config.product_cache_path / "mapping.db"
                ) as cache_mapping:
                    await fetch_and_install(
                        containerizer,
                        archive_client,
                        cache_mapping,
                        config.product_cache_path,
                        repositories,
                        repository_to_translated_options,
                        translators_task,
                        installers,
                        installation_path,
                        graph_path,
                        input.build_options,
                        model,
                    )

        if generators_path is not None:
            await generators(generators_path)

            stderr.write("Done.\n")

    except* Exception as e_group:
        log_exception(e_group)
        stderr.write("Aborting.\n")
