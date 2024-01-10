from asyncio import TaskGroup
from collections.abc import AsyncIterable
from pathlib import Path
from sys import stderr

from httpx import AsyncClient as HTTPClient
from httpx import AsyncHTTPTransport
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Dependency, Options, Package, PackageIDAndInfo
from PPpackage_utils.utils import TemporaryPipe, discard_async_iterable

from .settings import Settings


async def test_runner_run(debug: bool, settings: Settings):
    async with HTTPClient(
        http2=True,
        transport=AsyncHTTPTransport(http2=True, uds=str(settings.runner_socket_path)),
    ) as client:
        runner_workdir_path = settings.runner_workdir_path

        with (
            TemporaryPipe(runner_workdir_path) as stdin_pipe_path,
            TemporaryPipe(runner_workdir_path) as stdout_pipe_path,
        ):
            async with TaskGroup() as group:
                task = group.create_task(
                    client.post(
                        "http://localhost/user",
                        headers={"Authorization": f"Bearer {settings.runner_token}"},
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


def print_directory(directory: Path):
    print("PP test:", file=stderr)
    for member in directory.iterdir():
        print(f"\t{member.name}", file=stderr)


async def fetch(
    settings: Settings,
    state: None,
    options: Options,
    package: Package,
    dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> PackageIDAndInfo | AsyncIterable[str]:
    if generators_path is None:
        return create_generators()

    await test_runner_run(settings.debug, settings)

    await discard_async_iterable(dependencies)

    if installation_path is not None:
        print_directory(installation_path)

    print_directory(generators_path)

    return PackageIDAndInfo("id", None)
