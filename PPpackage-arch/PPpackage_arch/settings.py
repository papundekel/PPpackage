from pathlib import Path

from PPpackage_utils.utils import ContainerizerWorkdirInfo
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool
    cache_path: Path
    containerizer: str
    workdir: ContainerizerWorkdirInfo
