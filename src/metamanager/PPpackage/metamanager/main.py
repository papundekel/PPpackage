from asyncio import TaskGroup
from logging import getLogger
from pathlib import Path
from sys import stderr, stdin

from httpx import Client as HTTPClient
from PPpackage.utils.container import Containerizer
from PPpackage.utils.json.validate import validate_json_io, validate_json_io_path
from sqlitedict import SqliteDict

from .create_graph import create_graph, write_graph_to_file
from .exceptions import HandledException, handle_exception_group
from .fetch_and_install import fetch_and_install
from .generate import generate
from .installer import Installers
from .repository import Repositories
from .resolve import resolve
from .schemes import Config, Input
from .translators import Translators

logger = getLogger(__name__)


async def main(
    config_path: Path,
    installation_path: Path,
    generators_path: Path | None,
    graph_path: Path | None,
    just_resolve: bool,
) -> None:
    try:
        config = validate_json_io_path(Config, config_path)

        async with Repositories(
            config.repository_drivers, config.repositories, config.data_path
        ) as repositories:
            async with TaskGroup() as task_group:
                translators_task = task_group.create_task(
                    Translators(repositories, config.translators)
                )

                containerizer = Containerizer(config.containerizer)

                print("Pulling the solver image...", file=stderr)
                containerizer.pull_if_missing(
                    "docker.io/fackop/pppackage-solver:latest"
                )

                input = validate_json_io(Input, stdin.buffer)

                stderr.write("Resolving...\n")

                repository_to_translated_options, model = await resolve(
                    containerizer,
                    config.containerizer_workdir,
                    repositories,
                    translators_task,
                    input.options,
                    input.requirements,
                )

            with HTTPClient() as archive_client:
                product_cache_path = (
                    config.product_cache_path
                    if config.product_cache_path is not None
                    else config.data_path / "cache" / "product"
                )

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

                    if just_resolve:
                        stderr.write("Done.\n")
                        return

                    installers = Installers(config.installers)

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
                        product_cache_path,
                        input.build_options,
                        installation_path,
                        graph,
                    )

        if generators_path is not None:
            stderr.write(f"Generating to {generators_path}...\n")
            await generate(config.generators, graph, input.generators, generators_path)

        stderr.write("Done.\n")
    except* HandledException as exception_group:
        handle_exception_group(stderr, exception_group)
