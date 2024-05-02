from collections.abc import AsyncIterable
from contextlib import asynccontextmanager

from aiosqlite import Connection, Cursor

PREFIX = "pacman-real-"


def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]


def parse_provide(provide: str) -> tuple[str, str] | str:
    tokens = provide.rsplit("=", 1)

    if len(tokens) == 2:
        return tokens[0], tokens[1]
    else:
        return provide


def parse_package_name(full_package_name: str) -> tuple[str, str]:
    tokens = full_package_name[len(PREFIX) :].rsplit("-", 2)

    if len(tokens) != 3:
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version_no_pkgrel, pkgrel = tokens
    version = f"{version_no_pkgrel}-{pkgrel}"

    return name, version


@asynccontextmanager
async def transaction(connection: Connection):
    try:
        yield
    except:
        await connection.rollback()
        raise
    else:
        await connection.commit()


async def fetch_one(cursor: Cursor):
    row = await cursor.fetchone()

    if row is None:
        raise Exception("Row not found.")

    return row


async def query_provides(connection: Connection, name: str) -> AsyncIterable[str]:
    async with connection.execute(
        """
        SELECT provide FROM provides WHERE name = ?
        """,
        (name,),
    ) as cursor:
        async for row in cursor:
            yield row[0]
