from pydantic import BaseModel

from PPpackage.utils.container.schemes import ContainerizerConfig


class Parameters(BaseModel):
    containerizer: ContainerizerConfig
