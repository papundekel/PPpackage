from pathlib import Path

from conan.api.conan_api import ConanAPI

from .schemes import Parameters


async def install(parameters: Parameters, product_path: Path, installation_path: Path):
    api = ConanAPI(str(installation_path / "root" / ".conan2"))
    api.cache.restore(product_path)
