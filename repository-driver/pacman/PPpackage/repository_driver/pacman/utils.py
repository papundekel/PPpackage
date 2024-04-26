from collections.abc import Iterable

from sqlitedict import SqliteDict

from .schemes import RepositoryParameters


def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]


def package_provides(provides: Iterable[str]) -> Iterable[tuple[str, str] | str]:
    for provide in provides:
        tokens = provide.rsplit("=", 1)

        if len(tokens) == 2:
            yield tokens[0], tokens[1]
        else:
            yield provide


def Database(repository_parameters: RepositoryParameters) -> SqliteDict:
    return SqliteDict(repository_parameters.database_path / "database.sqlite")
