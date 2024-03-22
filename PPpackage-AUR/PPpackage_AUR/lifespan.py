from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from PPpackage_utils.utils import ensure_dir_exists, get_module_path
from sqlitedict import SqliteDict

from .settings import Settings


@dataclass(frozen=True)
class State:
    data_path: Path
    product_paths: SqliteDict


@asynccontextmanager
async def lifespan(settings: Settings):
    import PPpackage_AUR

    data_path = get_module_path(PPpackage_AUR).parent / "data"

    ensure_dir_exists(settings.cache_path)
    database_path = settings.cache_path / "db.sqlite"

    with SqliteDict(database_path, tablename="product_paths") as product_paths:
        yield State(data_path=data_path, product_paths=product_paths)
