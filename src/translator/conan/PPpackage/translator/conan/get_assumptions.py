from collections.abc import Iterable

from PPpackage.translator.interface.schemes import Data, Literal

from .schemes import Parameters


def get_assumptions(parameters: Parameters, data: Data) -> Iterable[Literal]:
    return []
