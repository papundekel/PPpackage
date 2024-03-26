from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Iterable
from dataclasses import dataclass

from PPpackage_utils.utils import asubprocess_communicate


async def is_package_from_aur(name: str) -> bool:
    process = await create_subprocess_exec(
        "pacman",
        "-Sp",
        name,
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    return_code = await process.wait()

    return return_code != 0


@dataclass(frozen=True)
class PackageInfo:
    version: str
    dependencies: Iterable[str]
    build_dependencies: Iterable[str]


def parse_list(line: str) -> Iterable[str]:
    tokens = line.split(":")[1].split()

    if len(tokens) == 1 and tokens[0] == "None":
        return []

    return tokens


async def fetch_info(name: str) -> PackageInfo:
    process = await create_subprocess_exec(
        "paru",
        "-Si",
        name,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=DEVNULL,
    )

    stdout = await asubprocess_communicate(process, "Error in `paru -Si`.")

    version = None
    dependencies = None
    build_dependencies = None

    for line in stdout.decode().splitlines():
        if line.startswith("Depends On"):
            dependencies = parse_list(line)
        elif line.startswith("Make Deps"):
            build_dependencies = parse_list(line)
        elif line.startswith("Version"):
            version = line.split(":")[1].rsplit("-", 1)[0].strip()

    if version is None:
        raise ValueError("Version not found.")

    if dependencies is None:
        raise ValueError("Dependencies not found.")

    if build_dependencies is None:
        raise ValueError("Build dependencies not found.")

    return PackageInfo(version, dependencies, build_dependencies)


def make_product_key(name: str, version: str, product_id: str) -> str:
    return f"{name}-{version}-{product_id}"
