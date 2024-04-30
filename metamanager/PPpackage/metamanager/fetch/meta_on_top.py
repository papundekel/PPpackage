from collections.abc import Iterable
from pathlib import Path

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import MetaOnTopProductDetail

from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes import NodeData

from . import fetch_package


@fetch_package.register
async def _(
    product_detail: MetaOnTopProductDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    return "simple"
