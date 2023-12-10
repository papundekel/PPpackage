from collections.abc import AsyncIterable, MutableSequence
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import (
    ManagerRequirement,
    Options,
    ResolutionGraph,
    ResolutionGraphNode,
)


async def resolve(
    debug: bool,
    data: Any,
    session_data: None,
    cache_path: Path,
    options: Options,
    requirements_list: AsyncIterable[AsyncIterable[str]],
) -> AsyncIterable[ResolutionGraph]:
    roots: MutableSequence[MutableSequence[str]] = []

    requirements_merged = set[str]()

    async for requirements in requirements_list:
        requirements_roots = []

        async for requirement in requirements:
            requirements_merged.add(requirement)
            requirements_roots.append(requirement)

        roots.append(requirements_roots)

    graph = [
        ResolutionGraphNode(
            name,
            "1.0.0",
            [],
            [ManagerRequirement(manager="arch", requirement="iana-etc")],
        )
        for name in requirements_merged
    ]

    yield ResolutionGraph(roots, graph)
