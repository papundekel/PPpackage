from pathlib import Path

from pydantic.dataclasses import dataclass
from pydantic_settings import BaseSettings


@dataclass
class RunnerSettings(BaseSettings):
    runner_socket_path: Path = Path("/run/PPpackage-runner.sock")
    runner_token: str = ""
    runner_workdir_path: Path = Path("/tmp/PPpackage-runner/workdirs/unset")
