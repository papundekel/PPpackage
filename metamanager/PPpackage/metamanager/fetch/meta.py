from collections.abc import Iterable
from pathlib import Path

from httpx import AsyncClient as HTTPClient
from PPpackage.repository_driver.interface.schemes import MetaBuildContextDetail

from PPpackage.metamanager.repository import Repository
from PPpackage.metamanager.schemes.node import NodeData

from . import fetch_package


@fetch_package.register
async def _(
    product_detail: MetaBuildContextDetail,
    client: HTTPClient,
    package: str,
    repository: Repository,
    dependencies: Iterable[tuple[str, NodeData]],
    destination_path: Path,
) -> str:
    return "simple"
