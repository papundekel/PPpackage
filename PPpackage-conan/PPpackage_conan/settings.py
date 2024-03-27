from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cache_path: Path
