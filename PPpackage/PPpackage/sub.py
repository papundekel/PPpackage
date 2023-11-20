from collections.abc import Hashable, Iterable, Set
from pathlib import Path
from sys import stderr
from typing import Any, cast

from PPpackage_utils.io import communicate_with_daemon
from PPpackage_utils.parse import (
    FetchInput,
    FetchOutput,
    FetchOutputValue,
    ManagerRequirement,
    Options,
    Product,
    ResolutionGraph,
    ResolutionGraphNode,
    model_dump_stream,
    model_validate_stream,
    models_dump_stream,
)
from PPpackage_utils.utils import (
    ImageType,
    MyException,
    RunnerRequestType,
    TemporaryPipe,
    frozendict,
)

from .utils import machine_id_relative_path, read_machine_id


async def update_database(debug: bool, cache_path: Path) -> None:
    pass


def check_requirements_list(
    requirements_list: Iterable[Iterable[Any]],
) -> Iterable[Iterable[str]]:
    requirements_list = list(requirements_list)

    for requirements in requirements_list:
        for requirement in requirements:
            if not isinstance(requirement, str):
                raise MyException("PPpackage: Requirements must be strings.")

    return cast(Iterable[Iterable[str]], requirements_list)


async def resolve(
    debug: bool,
    cache_path: Path,
    options: Options,
    requirements_list: Iterable[Iterable[Any]],
) -> Iterable[ResolutionGraph]:
    requirements_list = check_requirements_list(requirements_list)

    requirements_merged = set.union(set(), *requirements_list)

    graph = [
        ResolutionGraphNode(
            name,
            "1.0.0",
            [],
            [ManagerRequirement(manager="arch", requirement="iana-etc")],
        )
        for name in requirements_merged
    ]

    resolve_graph = ResolutionGraph(
        requirements_list,
        graph,
    )

    return [resolve_graph]


async def fetch(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    input: FetchInput,
) -> FetchOutput:
    async with communicate_with_daemon(debug, runner_path) as (
        runner_reader,
        runner_writer,
    ):
        machine_id = read_machine_id(Path("/") / machine_id_relative_path)

        model_dump_stream(debug, runner_writer, machine_id)
        model_dump_stream(debug, runner_writer, RunnerRequestType.RUN)
        model_dump_stream(debug, runner_writer, ImageType.TAG)
        model_dump_stream(debug, runner_writer, "docker.io/archlinux:latest")

        await runner_writer.drain()

        success = await model_validate_stream(debug, runner_reader, bool)

        if not success:
            raise MyException("PPpackage-sub: Failed to pull the build image.")

        models_dump_stream(debug, runner_writer, ["cat", "-"])

        with TemporaryPipe(runner_workdir_path) as stdin_pipe_path, TemporaryPipe(
            runner_workdir_path
        ) as stdout_pipe_path:
            model_dump_stream(
                debug,
                runner_writer,
                stdin_pipe_path.relative_to(runner_workdir_path),
            )

            model_dump_stream(
                debug,
                runner_writer,
                stdout_pipe_path.relative_to(runner_workdir_path),
            )

            models_dump_stream(debug, runner_writer, [])
            models_dump_stream(debug, runner_writer, [])

            with stdin_pipe_path.open("w") as stdin_pipe:
                stdin_pipe.write("ahoj!")

            with stdout_pipe_path.open("r") as stdout_pipe:
                print(stdout_pipe.read(), file=stderr)

        await runner_writer.drain()

        success = await model_validate_stream(debug, runner_reader, bool)

        if not success:
            raise MyException("PPpackage-sub: Failed to run the build image.")

    return FetchOutput(
        [
            FetchOutputValue(name=package.name, product_id="id", product_info=None)
            for package in input.packages
        ]
    )


async def generate(
    debug: bool,
    cache_path: Path,
    generators_path: Path,
    options: Options,
    products: Iterable[Product],
    generators: Iterable[str],
) -> None:
    pass


async def install(
    debug: bool,
    cache_path: Path,
    destination_path: Path,
    products: Iterable[Product],
) -> None:
    products_path = destination_path / "PP"

    products_path.mkdir(exist_ok=True)

    for product in products:
        product_path = products_path / product.name
        product_path.write_text(f"{product.version} {product.product_id}")
