from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    cache_path: Path = Path("/tmp")
