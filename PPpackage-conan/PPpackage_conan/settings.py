from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool
    cache_path: Path
