from asyncio import TaskGroup
from collections.abc import Awaitable, Iterable
from typing import Any

from .repository import Repository


async def repository_translate_options(
    repository: Repository, options: Any
) -> tuple[Repository, Any]:
    return repository, await repository.translate_options(options)


def translate_options(
    task_group: TaskGroup, repositories: Iterable[Repository], options: Any
) -> Iterable[Awaitable[tuple[Repository, Any]]]:
    for repository in repositories:
        yield task_group.create_task(repository_translate_options(repository, options))
