from datetime import datetime

from aiosqlite import Connection

from .utils import fetch_one


async def get(connection: Connection) -> str:
    async with connection.execute("SELECT * FROM epochs") as cursor:
        return (await fetch_one(cursor))[0]


async def update(connection: Connection) -> None:
    await connection.execute("UPDATE epochs SET epoch = ?", (str(datetime.now()),))
