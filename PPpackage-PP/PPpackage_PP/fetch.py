from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from PPpackage_utils.io import communicate_with_runner
from PPpackage_utils.parse import (
    Dependency,
    Options,
    Package,
    PackageIDAndInfo,
    dump_many,
    dump_one,
    load_one,
)
from PPpackage_utils.utils import (
    ImageType,
    RunnerInfo,
    RunnerRequestType,
    SubmanagerCommandFailure,
    TarFileInMemoryRead,
    TemporaryPipe,
    discard_async_iterable,
)

from .utils import Data


async def test_runner_run(debug: bool, runner_info: RunnerInfo):
    async with communicate_with_runner(debug, runner_info) as (
        runner_reader,
        runner_writer,
        runner_workdir_path,
    ):
        await dump_one(debug, runner_writer, RunnerRequestType.RUN)
        await dump_one(debug, runner_writer, ImageType.TAG)
        await dump_one(debug, runner_writer, "docker.io/archlinux:latest")

        success = await load_one(debug, runner_reader, bool)

        if not success:
            raise SubmanagerCommandFailure

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
                print("PP test:", stdout_pipe.read(), file=stderr)

        success = await load_one(debug, runner_reader, bool)

        if not success:
            raise SubmanagerCommandFailure


async def create_generators():
    yield "versions"


def print_tar(data: memoryview):
    with TarFileInMemoryRead(data) as tar:
        print("PP test:", file=stderr)
        for member in tar.getmembers():
            print(f"\t{member.name}", file=stderr)


async def fetch(
    debug: bool,
    data: Data,
    cache_path: Path,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation: memoryview | None,
    generators: memoryview | None,
) -> PackageIDAndInfo | AsyncIterable[str]:
    if generators is None:
        return create_generators()

    await test_runner_run(debug, data.runner_info)

    await discard_async_iterable(dependencies)

    if installation is not None:
        print_tar(installation)

    print_tar(generators)

    return PackageIDAndInfo("id", None)
