from collections.abc import Iterable

PREFIX = "pacman-"


def strip_version(name: str) -> str:
    return name.rsplit("<", 1)[0].rsplit(">", 1)[0].rsplit("=", 1)[0]


def package_provides(provides: Iterable[str]) -> Iterable[tuple[str, str] | str]:
    for provide in provides:
        tokens = provide.rsplit("=", 1)

        if len(tokens) == 2:
            yield tokens[0], tokens[1]
        else:
            yield provide


def parse_package_name(full_package_name: str) -> tuple[str, str]:
    tokens = full_package_name[len(PREFIX) :].rsplit("-", 2)

    if len(tokens) != 3:
        raise Exception(f"Invalid package: {full_package_name}")

    name, version_no_pkgrel, pkgrel = tokens
    version = f"{version_no_pkgrel}-{pkgrel}"

    return name, version
