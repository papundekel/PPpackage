from pathlib import Path
from typing import Annotated

from pydantic import AnyUrl, UrlConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    workdirs_path: Path = Path("/tmp")
    database_url: Annotated[
        AnyUrl, UrlConstraints(allowed_schemes=["sqlite+aiosqlite"])
    ] = AnyUrl("sqlite+aiosqlite:///db.sqlite")

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()