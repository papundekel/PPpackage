from dataclasses import dataclass

from PPpackage_utils.server import State as BaseState


@dataclass(frozen=True)
class State(BaseState):
    pass
