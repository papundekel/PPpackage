from collections.abc import Iterable, Mapping
from dataclasses import dataclass

type Data = Mapping[str, Iterable[dict[str, str]]]


@dataclass(frozen=True)
class Literal:
    symbol: str
    polarity: bool
