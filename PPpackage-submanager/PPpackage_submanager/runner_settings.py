from pathlib import Path

from pydantic.dataclasses import dataclass


@dataclass
class RunnerSettings:
    socket_path: Path = Path("/run/PPpackage-runner.sock")
    token: str = ""
    workdir_path: Path = Path("/tmp/PPpackage-runner/workdirs/unset")
