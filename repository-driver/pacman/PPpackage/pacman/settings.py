from pathlib import Path

from pydantic_settings import BaseSettings

from utils.utils import ContainerizerWorkdirInfo


class Settings(BaseSettings):
    cache_path: Path
    containerizer: str
    workdir: ContainerizerWorkdirInfo
