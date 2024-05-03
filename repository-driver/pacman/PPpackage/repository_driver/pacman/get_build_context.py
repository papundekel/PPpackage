from PPpackage.repository_driver.interface.schemes import (
    ArchiveBuildContextDetail,
    BuildContextDetail,
    ProductInfos,
)

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

    # TODO!!!

    archive_path = (
        state.cache_directory_path / f"{name}-{version}-{package.arch}.pkg.tar.zst"
    )

    if not archive_path.exists():
        archive_path = (
            state.cache_directory_path / f"{name}-{version}-{package.arch}.pkg.tar.xz"
        )

    return ArchiveBuildContextDetail(archive_path, "pacman")
