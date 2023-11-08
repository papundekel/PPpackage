from collections.abc import Iterable, Mapping, Set
from os import environ
from pathlib import Path
from sys import stderr
from typing import Any

from PPpackage_utils.io import (
    stream_read_line,
    stream_write_line,
    stream_write_string,
    stream_write_strings,
)
from PPpackage_utils.utils import MyException, Resolution, TemporaryPipe, frozendict

from .utils import communicate_with_daemon, machine_id_relative_path, read_machine_id


async def update_database(debug: bool, cache_path: Path) -> None:
    pass


async def resolve(
    debug: bool,
    cache_path: Path,
    requirements: Set[Any],
    options: Mapping[str, Any] | None,
) -> Set[Resolution]:
    lockfile = frozendict({name: "1.0.0" for name in set(requirements)})
    new_requirements = frozendict({"arch": frozenset(["iana-etc"])})

    return frozenset([Resolution(lockfile, new_requirements)])


async def fetch(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    versions: Mapping[str, str],
    options: Mapping[str, Any] | None,
    generators: Iterable[str],
    generators_path: Path,
) -> Mapping[str, str]:
    async with communicate_with_daemon(debug, runner_path) as (
        runner_reader,
        runner_writer,
    ):
        machine_id = read_machine_id(Path("/") / machine_id_relative_path)

        stream_write_string(debug, "PPpackage-sub", runner_writer, machine_id)

        stream_write_line(debug, "PPpackage-sub", runner_writer, "RUN")
        stream_write_line(debug, "PPpackage-sub", runner_writer, "IMAGE")
        stream_write_string(
            debug, "PPpackage-sub", runner_writer, "docker.io/archlinux:latest"
        )

        await runner_writer.drain()

        success = await stream_read_line(debug, "PPpackage-sub", runner_reader)

        if success != "SUCCESS":
            raise MyException("PPpackage-sub: Failed to pull the build image.")

        stream_write_strings(debug, "PPpackage-sub", runner_writer, ["cat", "-"])

        with TemporaryPipe(runner_workdir_path) as stdin_pipe_path, TemporaryPipe(
            runner_workdir_path
        ) as stdout_pipe_path:
            stream_write_string(
                debug,
                "PPpackage-sub",
                runner_writer,
                str(stdin_pipe_path.relative_to(runner_workdir_path)),
            )

            stream_write_string(
                debug,
                "PPpackage-sub",
                runner_writer,
                str(stdout_pipe_path.relative_to(runner_workdir_path)),
            )

            stream_write_strings(debug, "PPpackage-sub", runner_writer, [])
            stream_write_strings(debug, "PPpackage-sub", runner_writer, [])

            with stdin_pipe_path.open("w") as stdin_pipe:
                stdin_pipe.write("ahoj!")

            with stdout_pipe_path.open("r") as stdout_pipe:
                print(stdout_pipe.read(), file=stderr)

        await runner_writer.drain()

        success = await stream_read_line(debug, "PPpackage-sub", runner_reader)

        if success != "SUCCESS":
            raise MyException("PPpackage-sub: Failed to run the build image.")

    product_ids = {name: "id" for name in versions.keys()}

    return product_ids


async def install(
    debug: bool,
    cache_path: Path,
    destination_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    products_path = destination_path / "PP"

    products_path.mkdir(exist_ok=True)

    for name, version in versions.items():
        product_id = product_ids[name]

        product_path = products_path / name
        product_path.write_text(f"{version} {product_id}")
