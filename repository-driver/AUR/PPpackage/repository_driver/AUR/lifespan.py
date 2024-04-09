from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlitedict import SqliteDict

from utils.utils import ensure_dir_exists

from .settings import Settings


@dataclass(frozen=True)
class State:
    product_paths: SqliteDict


@asynccontextmanager
async def lifespan(settings: Settings):
    ensure_dir_exists(settings.cache_path)
    database_path = settings.cache_path / "db.sqlite"

    with SqliteDict(database_path, tablename="product_paths") as product_paths:
        yield State(product_paths=product_paths)
