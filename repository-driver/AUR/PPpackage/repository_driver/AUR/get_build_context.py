from collections.abc import AsyncIterable

from aiosqlite import Connection
from asyncstdlib import chain as async_chain
from asyncstdlib import list as async_list
from PPpackage.repository_driver.interface.schemes import (
    BuildContextDetail,
    MetaBuildContextDetail,
    ProductInfos,
    Requirement,
)

from .schemes import DriverParameters, RepositoryParameters
from .state import State
from .utils import PREFIX, parse_package_name, transaction


async def query_build_dependencies(
    connection: Connection, name: str
) -> AsyncIterable[str]:
    async with connection.execute(
        "SELECT dependency FROM build_dependencies WHERE name = ?", (name,)
    ) as cursor:
        async for row in cursor:
            yield row[0]


async def get_build_context(
    state: State,
    driver_parameters: DriverParameters,
    repository_parameters: RepositoryParameters,
    translated_options: None,
    full_package_name: str,
    runtime_product_infos: ProductInfos,
) -> BuildContextDetail:
    if not full_package_name.startswith(PREFIX):
        raise Exception(f"Invalid package name: {full_package_name}")

    name, version = parse_package_name(full_package_name)

    connection = state.connection

    async with transaction(connection):
        return MetaBuildContextDetail(
            await async_list(
                async_chain(
                    [
                        Requirement("pacman", "base-devel"),
                        Requirement("pacman", "git"),
                        Requirement(
                            "pacman", {"package": "ca-certificates", "no_provide": None}
                        ),
                        Requirement("pacman", "sudo"),
                        Requirement("pacman", "coreutils"),
                    ],
                    (
                        Requirement("pacman", dependency)
                        async for dependency in query_build_dependencies(
                            connection, name
                        )
                    ),
                )
            ),
            on_top=True,
            command=[
                "bash",
                "-c",
                "ls -l / 1>&2\n"
                "ls -l /etc 1>&2\n"
                "ls -l /etc/ssl 1>&2\n"
                "ls -l /etc/ssl/certs 1>&2\n"
                "ls -l /etc/ssl/certs/ca-certificates.crt 1>&2\n"
                "useradd builder\n"
                f"git clone https://aur.archlinux.org/{name}.git /tmp/workdir || exit 10\n"
                "chown -R builder:builder /tmp/workdir\n"
                "cd /tmp/workdir\n"
                "sudo --user builder makepkg || exit 20\n"
                "chown -R root:root /tmp/workdir\n"
                "mkdir /mnt/output\n"
                "mv /tmp/workdir/*.pkg.* /mnt/output/product\n"
                "chown root:root /mnt/output/product\n"
                "echo -n pacman > /mnt/output/installer\n",
            ],
        )
