from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from collections.abc import AsyncIterable, Iterable
from hashlib import sha1
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Protocol

from PPpackage_pacman_utils.schemes import ProductInfo
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import (
    Dependency,
    FetchRequest,
    Options,
    Package,
    ProductIDAndInfo,
)
from PPpackage_submanager.utils import containerizer_subprocess_exec
from PPpackage_utils.utils import TemporaryDirectory, asubprocess_wait
from PPpackage_utils.validation import load_object
from sqlitedict import SqliteDict

from .lifespan import State
from .settings import Settings
from .utils import fetch_info, is_package_from_aur, make_product_key


class Hash(Protocol):
    def update(self, value: bytes, /) -> None: ...


def hash_update_str(hash: Hash, value: str) -> None:
    hash.update(value.encode())


def update_product_id_hash(hash: Hash, dependency: Dependency) -> None:
    manager = dependency.manager

    hash_update_str(hash, manager)
    hash_update_str(hash, dependency.name)

    product_info_raw = dependency.product_info

    if product_info_raw is None:
        raise CommandException

    if manager not in {"arch", "AUR"}:
        raise CommandException(manager)

    product_info = load_object(ProductInfo, product_info_raw)
    hash_update_str(hash, product_info.version)
    hash_update_str(hash, product_info.product_id)


def make_product_id(dependencies: Iterable[Dependency]):
    product_id_hash = sha1()

    for dependency in sorted(
        dependencies, key=lambda dependency: (dependency.manager, dependency.name)
    ):
        update_product_id_hash(product_id_hash, dependency)

    product_id = product_id_hash.hexdigest()

    return product_id


async def build(
    cache_path: Path,
    containerizer: str,
    product_paths: SqliteDict,
    package: Package,
    build_context_path: Path,
    product_key: str,
):
    product_path_dir = Path(mkdtemp(dir=cache_path))

    try:
        with TemporaryDirectory() as build_path:
            with open(build_path / "PKGBUILD", "w") as file:
                process = await create_subprocess_exec(
                    "paru",
                    "--getpkgbuild",
                    "--print",
                    package.name,
                    stdin=DEVNULL,
                    stdout=file,
                    stderr=DEVNULL,
                )

                await asubprocess_wait(process, CommandException())

            PKGDEST = "/mnt/package"
            WORKDIR = "/mnt/build"

            async with containerizer_subprocess_exec(
                containerizer,
                "run",
                "--rm",
                "--interactive",
                "--userns=keep-id",
                "--mount",
                f"type=bind,source={product_path_dir.absolute()},target={PKGDEST}",
                "--mount",
                f"type=bind,source={build_path.absolute()},target={WORKDIR}",
                "--env",
                f"PKGDEST={PKGDEST}",
                "--workdir",
                WORKDIR,
                "--rootfs",
                str(build_context_path.absolute()),
                "makepkg",
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
            ) as process:
                await asubprocess_wait(process, CommandException())

        product_path = next(product_path_dir.iterdir())

        product_paths[product_key] = product_path
        product_paths.commit()
    except:
        product_path_dir.rmdir()
        raise


async def request_build_context(build_dependencies: Iterable[str]):
    yield "arch", "base-devel"  # implicit, see https://wiki.archlinux.org/title/makepkg#Usage

    for dependency in build_dependencies:
        is_from_aur = await is_package_from_aur(dependency)

        submanager_name = "AUR" if is_from_aur else "arch"

        yield submanager_name, dependency


async def empty_generators():
    for _ in []:
        yield ""


async def fetch(
    settings: Settings,
    state: State,
    options: Options,
    package: Package,
    async_dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> ProductIDAndInfo | FetchRequest:
    dependencies = [dependency async for dependency in async_dependencies]

    product_id = make_product_id(dependencies)

    product_key = make_product_key(package.name, package.version, product_id)

    if product_key not in state.product_paths:
        package_info = await fetch_info(package.name)
        build_dependencies = package_info.build_dependencies

        if installation_path is None:
            return FetchRequest(
                request_build_context(build_dependencies), empty_generators()
            )

        await build(
            settings.cache_path,
            settings.containerizer,
            state.product_paths,
            package,
            installation_path,
            product_key,
        )

    return ProductIDAndInfo(
        product_id, ProductInfo(version=package.version, product_id=product_id)
    )
