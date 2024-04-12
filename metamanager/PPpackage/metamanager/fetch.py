from asyncio import TaskGroup
from collections.abc import Iterable
from functools import singledispatch
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Any

from httpx import AsyncClient as HTTPClient
from networkx import MultiDiGraph, topological_generations
from PPpackage.repository_driver.interface.schemes import (
    ArchiveProductDetail,
    PackageDetail,
)

from metamanager.PPpackage.metamanager.repository import Repository

from .exceptions import SubmanagerCommandFailure


@singledispatch
async def fetch_package(
    product_detail: Any,
    client: HTTPClient,
    package: str,
    repository: Repository,
) -> tuple[Path, str]:
    raise NotImplementedError


@fetch_package.register
async def _(
    product_detail: ArchiveProductDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
) -> tuple[Path, str]:
    url_or_path = product_detail.archive

    if isinstance(url_or_path, Path):
        url = f"{repository.get_url()}/{url_or_path}"
    else:
        url = str(url_or_path)

    async with client.stream("GET", url, follow_redirects=True) as response:
        if not response.is_success:
            raise SubmanagerCommandFailure(
                f"Failed to fetch package {package} from {url}."
                f"{(await response.aread()).decode()}"
            )

        temp_dir = Path(mkdtemp())

        path = temp_dir / "product"

        with path.open("wb") as file:
            async for chunk in response.aiter_raw():
                file.write(chunk)

    return path, product_detail.installer


async def fetch(client: HTTPClient, graph: MultiDiGraph) -> None:
    stderr.write("Fetching package products...\n")

    generations: Iterable[Iterable[str]] = topological_generations(
        graph.reverse(copy=False)
    )

    for generation in generations:
        async with TaskGroup() as group:
            for package in generation:
                detail: PackageDetail = graph.nodes[package]["detail"]

                node = graph.nodes[package]

                node["product"] = group.create_task(
                    fetch_package(detail.product, client, package, node["repository"])
                )

        for package in generation:
            node = graph.nodes[package]

            node["product"] = node["product"].result()