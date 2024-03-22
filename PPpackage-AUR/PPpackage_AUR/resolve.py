from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable, MutableSequence

from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import (
    ManagerRequirement,
    Options,
    ResolutionGraph,
    ResolutionGraphNode,
)
from PPpackage_utils.utils import asubprocess_wait

from .lifespan import State
from .settings import Settings
from .utils import PackageInfo, fetch_info


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
    state: State,
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
                package_names_with_info[package_name] = await fetch_info(package_name)

            requirements_roots.append(package_name)

        roots.append(requirements_roots)

    graph = [
        await create_node(name, info) for name, info in package_names_with_info.items()
    ]

    yield ResolutionGraph(roots, graph)
