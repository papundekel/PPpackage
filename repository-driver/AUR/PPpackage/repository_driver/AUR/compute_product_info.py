from sys import stderr

from PPpackage.repository_driver.interface.schemes import (
    DependencyProductInfos,
    ProductInfo,
)
from sqlitedict import SqliteDict

from .schemes import AURPackage, DriverParameters, RepositoryParameters
from .utils import PREFIX, parse_package_name, strip_version


async def compute_product_info(
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    dependency_product_infos: DependencyProductInfos,
) -> ProductInfo:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    print(f"{full_package_name}: {dependency_product_infos}", file=stderr)

    with SqliteDict(
        repository_parameters.database_path / "database.sqlite",
        tablename="packages",
    ) as database:
        package: AURPackage = database[name]

    return {
        f"pacman-{strip_version(provide)}": {"version": f"{version}"}
        for provide in package.Provides
    } | {
        f"pacman-{name}": {
            "version": f"{version}",
            "dependency-versions": {
                dependency[len("pacman-") :]: next(iter(product_infos.values()))[
                    "version"
                ]
                for dependency, product_infos in dependency_product_infos.items()
            },
        }
    }
