from datetime import datetime
from pathlib import Path

from sqlitedict import SqliteDict


def get(database_path: Path):
    with SqliteDict(database_path) as database:
        return str(database["epoch"])


def update(database_path: Path):
    with SqliteDict(database_path) as database:
        database["epoch"] = str(datetime.now())
        database.commit()
