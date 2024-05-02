from dataclasses import dataclass

from aiosqlite import Connection


@dataclass(frozen=True)
class State:
    connection: Connection
