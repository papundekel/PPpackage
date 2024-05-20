from sys import stderr

from httpx import ConnectTimeout
from PPpackage.repository_driver.interface.schemes import (
    ArchiveBuildContextDetail,
    BuildContextDetail,
    ProductInfos,
)
from pydantic import AnyUrl

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name


async def get_build_context(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    package = state.database.get_pkg(name)

    if package is None:
        raise Exception(f"Invalid package: {full_package_name}")

    if package.version != version:
        raise Exception(f"Invalid package: {full_package_name}")

    name_with_arch = f"{name}-{version}-{package.arch}"

    for suffix in ["pkg.tar.zst", "pkg.tar.xz"]:
        url = f"https://archive.archlinux.org/packages/{name[0]}/{name}/{name_with_arch}.{suffix}"

        try:
            response = state.http_client.head(url, timeout=None)
        except ConnectTimeout:
            print(f"Timeout {url}", file=stderr)
            raise
        else:
            if response.status_code == 200:
                return ArchiveBuildContextDetail(AnyUrl(url), "pacman")

    raise Exception(f"Invalid package: {full_package_name}")
