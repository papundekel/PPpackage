from asyncio import TaskGroup
from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from httpx import AsyncClient as HTTPClient
from httpx import AsyncHTTPTransport
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Dependency, Options, Package, PackageIDAndInfo
from PPpackage_utils.tar import TarFileInMemoryRead
from PPpackage_utils.utils import TemporaryPipe, discard_async_iterable

from .settings import settings
from .utils import State


async def test_runner_run(debug: bool):
    async with HTTPClient(
        transport=AsyncHTTPTransport(uds=str(settings.runner.socket_path))
    ) as client:
        runner_workdir_path = settings.runner.workdir_path

        with (
            TemporaryPipe(runner_workdir_path) as stdin_pipe_path,
            TemporaryPipe(runner_workdir_path) as stdout_pipe_path,
        ):
            async with TaskGroup() as group:
                task = group.create_task(
                    client.post(
                        "http://localhost/user",
                        headers={"Authorization": f"Bearer {settings.runner.token}"},
                        params={
                            "tag": "docker.io/archlinux:latest",
                            "args": ["cat", "-"],
                            "stdin_pipe_path": str(
                                stdin_pipe_path.relative_to(runner_workdir_path)
                            ),
                            "stdout_pipe_path": str(
                                stdout_pipe_path.relative_to(runner_workdir_path)
                            ),
                        },
                    )
                )

                with stdin_pipe_path.open("w") as stdin_pipe:
                    stdin_pipe.write("ahoj!")

                with stdout_pipe_path.open("r") as stdout_pipe:
                    print("PP test:", stdout_pipe.read(), file=stderr)

        if not (200 <= task.result().status_code < 300):
            raise CommandException


async def create_generators():
    yield "versions"


def print_tar(data: memoryview):
    with TarFileInMemoryRead(data) as tar:
        print("PP test:", file=stderr)
        for member in tar.getmembers():
            print(f"\t{member.name}", file=stderr)


async def fetch(
    debug: bool,
    state: State,
    cache_path: Path,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation: memoryview | None,
    generators: memoryview | None,
) -> PackageIDAndInfo | AsyncIterable[str]:
    if generators is None:
        return create_generators()

    await test_runner_run(debug)

    await discard_async_iterable(dependencies)

    if installation is not None:
        print_tar(installation)

    print_tar(generators)

    return PackageIDAndInfo("id", None)
