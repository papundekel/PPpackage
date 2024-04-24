from collections.abc import Iterable


def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]


def package_provides(provides: Iterable[str]) -> Iterable[tuple[str, str] | str]:
    for provide in provides:
        tokens = provide.rsplit("=", 1)

        if len(tokens) == 2:
            yield tokens[0], tokens[1]
        else:
            yield provide
