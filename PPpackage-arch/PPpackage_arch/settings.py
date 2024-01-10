from pathlib import Path

from PPpackage_submanager.runner_settings import RunnerSettings


class Settings(RunnerSettings):
    debug: bool = False
    cache_path: Path = Path("/tmp")
