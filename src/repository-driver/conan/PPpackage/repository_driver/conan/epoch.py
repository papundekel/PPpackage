from datetime import datetime
from pathlib import Path


def get(path: Path) -> str:
    with path.open("r") as file:
        return file.read()


def update(path: Path):
    with path.open("w") as file:
        file.write(str(datetime.now()))
