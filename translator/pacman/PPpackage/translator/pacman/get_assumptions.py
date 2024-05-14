from collections.abc import Iterable

from PPpackage.translator.interface.schemes import Data, Literal

from .schemes import Parameters
from .utils import process_symbol


def get_assumptions(parameters: Parameters, data: Data) -> Iterable[Literal]:
    for group, symbols in data.items():
        if not group.startswith("pacman-"):
            continue

        is_any_arch = False
        aurs = list[dict[str, str]]()

        for symbol in symbols:
            if "AUR" in symbol:
                aurs.append(symbol)
            else:
                is_any_arch = True

        if is_any_arch:
            for symbol in aurs:
                package, _ = process_symbol(group[len("pacman-") :], symbol)
                yield Literal(f"pacman-{package}", False)

    return []
