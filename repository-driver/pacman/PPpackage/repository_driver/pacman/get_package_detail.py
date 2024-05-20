from itertools import chain

from PPpackage.repository_driver.interface.schemes import PackageDetail

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, strip_version


async def get_package_detail(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
) -> PackageDetail | None:
    if not full_package_name.startswith(PREFIX):
        return None

    name, version = parse_package_name(full_package_name)

    package = state.database.get_pkg(name)

    if package is None:
        return None

    if package.version != version:
        return None

    return PackageDetail(
        frozenset(
            chain(
                [f"pacman-{name}"],
                (f"pacman-{strip_version(provide)}" for provide in package.provides),
            )
        ),
        frozenset(
            f"pacman-{strip_version(dependency)}"
            for dependency in package.depends
            if not (
                name == "libglvnd"
                and (dependency == "mesa" or dependency == "opengl-driver")
            )
        ),
    )
