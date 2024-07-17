from collections.abc import Awaitable
from pathlib import Path
from typing import TypedDict

from PPpackage.repository_driver.interface.schemes import PackageDetail, ProductInfo

from PPpackage.metamanager.repository import Repository


class NodeData(TypedDict):
    repository: Repository
    detail: PackageDetail
    product_info: Awaitable[ProductInfo]
    product: Awaitable[tuple[Path, str]]
