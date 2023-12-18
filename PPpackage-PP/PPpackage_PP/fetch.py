from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr
from typing import Any

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
from PPpackage_utils.submanager import BuildRequest, BuildResult
from PPpackage_utils.utils import (
    ImageType,
    RunnerInfo,
    RunnerRequestType,
    SubmanagerCommandFailure,
    TarFileInMemoryRead,
    TemporaryPipe,
    discard_async_iterable,
)


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


async def generators():
    yield "versions"


async def fetch(
    debug: bool,
    runner_info: RunnerInfo,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> AsyncIterable[PackageIDAndInfo | BuildRequest]:
    await test_runner_run(debug, runner_info)

    async for package, dependencies in packages:
        yield BuildRequest((package.name, generators()))

        await discard_async_iterable(dependencies)

    received_installations = set[str]()
    received_generators = set[str]()

    async for build_result in build_results:
        package_name = build_result.name

        with TarFileInMemoryRead(build_result.data) as tar:
            print("PP test:", file=stderr)
            for member in tar.getmembers():
                print(f"\t{member.name}", file=stderr)

        if build_result.is_installation:
            received_installations.add(package_name)
        else:
            received_generators.add(package_name)

        if (
            package_name in received_installations
            and package_name in received_generators
        ):
            yield PackageIDAndInfo(package_name, "id", None)
