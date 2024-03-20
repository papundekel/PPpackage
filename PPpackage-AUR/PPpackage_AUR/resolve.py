from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable, Iterable, MutableSequence
from dataclasses import dataclass
from sys import stderr

from PPpackage_submanager.schemes import (
    ManagerRequirement,
    Options,
    ResolutionGraph,
    ResolutionGraphNode,
)
from PPpackage_utils.utils import asubprocess_communicate

from .settings import Settings


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


def split_version_requirement(requirement: str) -> str:
    return requirement.split("==")[0].split(">=")[0]


@dataclass(frozen=True)
class PackageInfo:
    version: str
    dependencies: Iterable[str]


async def fetch_info(name: str) -> PackageInfo:
    process = await create_subprocess_exec(
        "paru",
        "-Si",
        name,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=None,
    )

    stdout = await asubprocess_communicate(process, "Error in `paru -Si`.")

    dependencies = []
    version = ""

    for line in stdout.decode().splitlines():
        if line.startswith("Depends On"):
            dependencies = line.split(":")[1].split()
        elif line.startswith("Version"):
            version = line.split(":")[1].strip().rsplit("-", 1)[0]

    return PackageInfo(version, dependencies)


async def create_node(name: str, info: PackageInfo) -> ResolutionGraphNode:
    aur_dependencies = []
    arch_dependencies = []

    for dependency in info.dependencies:
        if await is_package_from_aur(dependency):
            aur_dependencies.append(dependency)
        else:
            arch_dependencies.append(dependency)

    return ResolutionGraphNode(
        name,
        info.version,
        [
            split_version_requirement(aur_dependency)
            for aur_dependency in aur_dependencies
        ],
        [
            ManagerRequirement(manager="arch", requirement=arch_dependency)
            for arch_dependency in arch_dependencies
        ]
        + [
            ManagerRequirement(manager="AUR", requirement=aur_dependency)
            for aur_dependency in aur_dependencies
        ],
    )


async def resolve(
    settings: Settings,
    state: None,
    options: Options,
    requirements_list: AsyncIterable[AsyncIterable[str]],
) -> AsyncIterable[ResolutionGraph]:
    roots: MutableSequence[MutableSequence[str]] = []

    package_names_with_info = dict[str, PackageInfo]()

    async for requirements in requirements_list:
        requirements_roots = []

        async for requirement in requirements:
            package_name = split_version_requirement(requirement)

            if package_name not in package_names_with_info:
                dependencies = await fetch_info(package_name)
                package_names_with_info[package_name] = dependencies

            requirements_roots.append(package_name)

        roots.append(requirements_roots)

    graph = [
        await create_node(name, info) for name, info in package_names_with_info.items()
    ]

    yield ResolutionGraph(roots, graph)
