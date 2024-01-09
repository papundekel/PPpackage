from pathlib import Path
from typing import Annotated

from PPpackage_submanager.runner_settings import RunnerSettings
from pydantic import AnyUrl, UrlConstraints
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = True
    runner: RunnerSettings = RunnerSettings()
    database_url: Annotated[
        AnyUrl, UrlConstraints(allowed_schemes=["sqlite+aiosqlite"])
    ] = AnyUrl("sqlite+aiosqlite:///db.sqlite")
    cache_path: Path = Path("/tmp")


settings = Settings()
