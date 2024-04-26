from contextlib import contextmanager
from pathlib import Path

from sqlitedict import SqliteDict


def get(database_path: Path):
    with SqliteDict(database_path) as database:
        return str(database["epoch"])


@contextmanager
def update(database_path: Path):
    with SqliteDict(database_path) as database:
        if "epoch" in database:
            epoch = database["epoch"]
        else:
            epoch = 0

        yield epoch

        database["epoch"] = epoch + 1
        database.commit()
