from PPpackage.container_utils.schemes import ContainerizerConfig
from pydantic import BaseModel


class Parameters(BaseModel):
    containerizer: ContainerizerConfig
