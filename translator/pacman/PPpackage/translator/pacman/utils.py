from collections.abc import Mapping


def process_symbol(name: str, symbol: Mapping[str, str]) -> tuple[str, str | None]:
    provider = symbol.get("provider")
    version = symbol.get("version")

    return provider if provider is not None else f"{name}-{version}", version
