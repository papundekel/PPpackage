from pathlib import Path

from pydantic import BaseModel

from PPpackage.utils.container.schemes import ContainerizerConfig


class Parameters(BaseModel):
    containerizer: ContainerizerConfig
    fakealpm_install_path: Path = Path("/") / "usr" / "local"
