from pathlib import Path

from starlette.config import Config

config = Config(".env")


DEBUG = config("DEBUG", cast=bool, default=True)
WORKDIRS_PATH = config("WORKDIRS_PATH", cast=Path)
DATABASE_URL = config(
    "DATABASE_URL", cast=str, default="sqlite+aiosqlite:///PPpackage-runner.db"
)
