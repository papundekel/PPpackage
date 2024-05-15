from asyncio import TaskGroup
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin
from traceback import print_exc
from typing import IO

from httpx import AsyncClient as HTTPClient
from PPpackage.container_utils import Containerizer
from pydantic import ValidationError
from sqlitedict import SqliteDict

from PPpackage.utils.validation import validate_json

from .create_graph import create_graph, write_graph_to_file
from .fetch_and_install import fetch_and_install
from .generate import generate
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


async def main(
    config_path: Path,
    installation_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
) -> None:
    config = parse_config(config_path)

    containerizer = Containerizer(config.containerizer)
    installers = Installers(config.installers)
    product_cache_path = config.product_cache_path

    input = parse_input(stdin.buffer)

    async with Repositories(
        config.repository_drivers, config.repositories
    ) as repositories:
        async with TaskGroup() as task_group:
            translators_task = task_group.create_task(
                Translators(repositories, config.requirement_translators)
            )

            stderr.write("Resolving...\n")

            repository_to_translated_options, model = await resolve(
                containerizer,
                config.containerizer_workdir,
                repositories,
                translators_task,
                input.options,
                input.requirements,
            )

        async with HTTPClient(http2=True) as archive_client:
            product_cache_path.mkdir(parents=True, exist_ok=True)

            with SqliteDict(product_cache_path / "mapping.db") as cache_mapping:
                stderr.write("Creating graph...\n")

                graph = await create_graph(
                    repositories, repository_to_translated_options, model
                )

                stderr.write("Resolved packages:\n")
                for package in sorted(graph.nodes):
                    stderr.write(f"\t{package}\n")

                if graph_path is not None:
                    write_graph_to_file(graph, graph_path)
                    stderr.write(f"Graph written to {graph_path}.\n")

                stderr.write(f"Fetching and installing to {installation_path}...\n")

                await fetch_and_install(
                    containerizer,
                    config.containerizer_workdir,
                    repositories,
                    repository_to_translated_options,
                    translators_task,
                    installers,
                    cache_mapping,
                    archive_client,
                    config.product_cache_path,
                    input.build_options,
                    installation_path,
                    graph,
                )

    if generators_path is not None:
        stderr.write(f"Generating to {generators_path}...\n")
        await generate(config.generators, graph, input.generators, generators_path)

    stderr.write("Done.\n")
