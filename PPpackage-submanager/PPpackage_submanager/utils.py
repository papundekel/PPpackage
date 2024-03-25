from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Generator, Iterable, Mapping
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, Optional, TypeVar

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse as BaseStreamingResponse
from jinja2 import Template as Jinja2Template
from PPpackage_utils.http_stream import AsyncChunkReader
from PPpackage_utils.utils import TemporaryDirectory, asubprocess_communicate
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from .exceptions import CommandException


@asynccontextmanager
async def get_session_from_engine(engine: AsyncEngine):
    async with AsyncSession(engine) as session:
        yield session


def get_state(request: Request):
    return request.app.state.state


async def get_session(request: Request):
    async with get_session_from_engine(request.app.state.engine) as session:
        yield session


def HTTP401Exception():
    return HTTPException(status_code=HTTP_401_UNAUTHORIZED)


def HTTP403Exception():
    return HTTPException(status_code=HTTP_403_FORBIDDEN)


def HTTP404Exception():
    return HTTPException(status_code=HTTP_404_NOT_FOUND)


def HTTP400Exception():
    return HTTPException(status_code=HTTP_400_BAD_REQUEST)


Model = TypeVar("Model", bound=SQLModel)


async def get_not_primary(
    session: AsyncSession, ModelDB: type[Model], column: Any, pk: Any, *options: Any
) -> Model | None:
    query = select(ModelDB).where(column == pk)

    if options != ():
        query = query.options(*options)

    instance_db = (await session.exec(query)).first()
    return instance_db


def StreamingResponse(
    status_code: int,
    generator: Iterable[memoryview] | AsyncIterable[memoryview],
):
    if isinstance(generator, Iterable):
        generator_wrapped = (bytes(chunk) for chunk in generator)
    else:
        generator_wrapped = (bytes(chunk) async for chunk in generator)

    return BaseStreamingResponse(
        generator_wrapped,
        status_code=status_code,
        media_type="application/octet-stream",
    )


def _command_exception(f):
    def decorator(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            raise CommandException

    return decorator


class Installations:
    def __init__(self, max: int):
        self.mapping = dict[int, memoryview]()
        self.max = max
        self.i = 0

    @_command_exception
    def _find_new_i(self, i: int) -> int:
        new_i = i + 1

        while new_i in self.mapping:
            if new_i >= self.max:
                new_i = 0

            new_i += 1

        return new_i

    @_command_exception
    def add(self, installation: memoryview) -> str:
        i = self.i

        self.mapping[i] = installation

        self.i = self._find_new_i(i)

        return str(i)

    @_command_exception
    def put(self, id: str, installation: memoryview) -> None:
        i = int(id)

        self.mapping[i] = installation

    @_command_exception
    def get(self, id: str) -> memoryview:
        i = int(id)

        return self.mapping[i]

    @_command_exception
    def remove(self, id: str) -> None:
        i = int(id)

        del self.mapping[i]


def HTTPRequestReader(request: Request):
    return AsyncChunkReader(memoryview(chunk) async for chunk in request.stream())


@contextmanager
def jinja_render_temp_file(
    template: Jinja2Template,
    template_context: Mapping[str, Any],
    suffix: Optional[str] = None,
) -> Generator[_TemporaryFileWrapper, Any, Any]:
    with NamedTemporaryFile(mode="w", suffix=suffix) as file:
        template.stream(**template_context).dump(file)

        file.flush()

        yield file


@asynccontextmanager
async def containerizer_subprocess_exec(
    url: str, *args, stdin: Any, stdout: Any, stderr: Any
):
    with (
        TemporaryDirectory() as empty_directory,
        NamedTemporaryFile() as containers_conf,
    ):
        yield await create_subprocess_exec(
            "podman-remote",
            "--url",
            url,
            *args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env={
                "CONTAINERS_CONF": containers_conf.name,
                "XDG_DATA_HOME": empty_directory,
            },
        )


async def containerizer_build(url: str, dockerfile_path: Path) -> str:
    with TemporaryDirectory() as empty_directory:
        async with containerizer_subprocess_exec(
            url,
            "build",
            "--quiet",
            "--file",
            dockerfile_path,
            empty_directory,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=None,
        ) as process:
            build_stdout = await asubprocess_communicate(
                process, "Error in podman-remote build"
            )

    image_id = build_stdout.decode().strip()

    return image_id
