from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from PPpackage_utils.io import communicate_with_runner
from PPpackage_utils.parse import (
    Dependency,
    IDAndInfo,
    Options,
    Package,
    PackageIDAndInfo,
    dump_many,
    dump_one,
    load_one,
)
from PPpackage_utils.utils import (
    MACHINE_ID_RELATIVE_PATH,
    ImageType,
    MyException,
    RunnerRequestType,
    TemporaryPipe,
    read_machine_id,
)


async def fetch_send(
    debug: bool,
    runner_path: Path,
    runner_workdir_path: Path,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
):
    async for package, dependencies in packages:
        yield PackageIDAndInfo(
            name=package.name, id_and_info=IDAndInfo(product_id="id", product_info=None)
        )

        async for _ in dependencies:
            pass

    machine_id = read_machine_id(Path("/"))

    async with communicate_with_runner(debug, runner_path, machine_id) as (
        runner_reader,
        runner_writer,
    ):
        await dump_one(debug, runner_writer, RunnerRequestType.RUN)
        await dump_one(debug, runner_writer, ImageType.TAG)
        await dump_one(debug, runner_writer, "docker.io/archlinux:latest")

        success = await load_one(debug, runner_reader, bool)

        if not success:
            raise MyException("PPpackage-sub: Failed to pull the build image.")

        await dump_many(debug, runner_writer, ["cat", "-"])

        with TemporaryPipe(runner_workdir_path) as stdin_pipe_path, TemporaryPipe(
            runner_workdir_path
        ) as stdout_pipe_path:
            await dump_one(
                debug,
                runner_writer,
                stdin_pipe_path.relative_to(runner_workdir_path),
            )

            await dump_one(
                debug,
                runner_writer,
                stdout_pipe_path.relative_to(runner_workdir_path),
            )

            await dump_many(debug, runner_writer, [])
            await dump_many(debug, runner_writer, [])

            with stdin_pipe_path.open("w") as stdin_pipe:
                stdin_pipe.write("ahoj!")

            with stdout_pipe_path.open("r") as stdout_pipe:
                print(stdout_pipe.read(), file=stderr)

        success = await load_one(debug, runner_reader, bool)

        if not success:
            raise MyException("PPpackage-sub: Failed to run the build image.")
