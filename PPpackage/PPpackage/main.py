from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence
from pathlib import Path
from sys import stderr, stdin

from networkx import MultiDiGraph
from networkx import topological_generations as base_topological_generations
from PPpackage_utils.app import AsyncTyper, run
from PPpackage_utils.parse import load_from_bytes
from PPpackage_utils.utils import (
    TarFileInMemoryRead,
    TarFileInMemoryWrite,
    wipe_directory,
)
from typer import Option as TyperOption
from typing_extensions import Annotated

from .fetch import fetch
from .generate import generate
from .install import install
from .parse import Input
from .resolve import resolve
from .update_database import update_database
from .utils import NodeData

app = AsyncTyper()


def topological_generations(
    graph: MultiDiGraph,
) -> Iterable[Mapping[str, Iterable[tuple[str, NodeData]]]]:
    for generation in base_topological_generations(graph):
        manager_nodes: MutableMapping[str, MutableSequence[tuple[str, NodeData]]] = {}

        for manager_and_name in generation:
            manager_nodes.setdefault(manager_and_name.manager, []).append(
                (manager_and_name.name, graph.nodes[manager_and_name])
            )

        yield manager_nodes


@app.command()
async def main_command(
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    do_update_database: Annotated[
        bool, TyperOption("--update-database/--no-update-database")
    ] = False,
    debug: bool = False,
    resolve_iteration_limit: int = 10,
) -> None:
    input_json_bytes = stdin.buffer.read()

    input = load_from_bytes(debug, Input, input_json_bytes)

    if do_update_database:
        managers = input.requirements.keys()
        await update_database(debug, managers, cache_path)

    graph = await resolve(
        debug, resolve_iteration_limit, cache_path, input.requirements, input.options
    )

    reversed_graph = graph.reverse(copy=False)

    generations = list(topological_generations(reversed_graph))

    await fetch(
        debug,
        runner_path,
        runner_workdir_path,
        cache_path,
        input.options,
        graph,
        generations,
    )

    generators_bytes = await generate(
        debug,
        cache_path,
        input.generators,
        graph.nodes(data=True),
        input.options,
    )

    with TarFileInMemoryRead(generators_bytes) as generators_tar:
        generators_tar.extractall(generators_path)

    with TarFileInMemoryWrite() as old_installation_tar:
        old_installation_tar.add(str(destination_path), "")

    old_installation = old_installation_tar.data

    wipe_directory(destination_path)

    new_installation = await install(
        debug,
        cache_path,
        runner_path,
        runner_workdir_path,
        old_installation,
        generations,
    )

    with TarFileInMemoryRead(new_installation) as new_installation_tar:
        new_installation_tar.extractall(destination_path)

    stderr.write("Done.\n")


def main():
    run(app, "PPpackage")
