from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

from PPpackage_utils.parse import Dependency, Options, Package, PackageIDAndInfo
from PPpackage_utils.submanager import BuildRequest, BuildResult
from PPpackage_utils.utils import RunnerInfo


async def fetch(
    debug: bool,
    runner_info: RunnerInfo,
    session_data: Any,
    cache_path: Path,
    options: Options,
    packages: AsyncIterable[tuple[Package, AsyncIterable[Dependency]]],
    build_results: AsyncIterable[BuildResult],
) -> AsyncIterable[PackageIDAndInfo | BuildRequest]:
    yield PackageIDAndInfo("aur", "id", None)
