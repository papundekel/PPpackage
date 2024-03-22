from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import AsyncIterable
from hashlib import sha1
from itertools import chain
from pathlib import Path
from sys import stderr
from tempfile import mkdtemp
from typing import Protocol

from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader as Jinja2FileSystemLoader
from jinja2 import select_autoescape as jinja2_select_autoescape
from PPpackage_submanager.exceptions import CommandException
from PPpackage_submanager.schemes import Dependency, Options, Package, ProductIDAndInfo
from PPpackage_submanager.utils import jinja_render_temp_file
from PPpackage_utils.utils import (
    TemporaryDirectory,
    asubprocess_communicate,
    asubprocess_wait,
)
from PPpackage_utils.validation import load_object

from .lifespan import State
from .schemes import ProductInfo
from .settings import Settings
from .utils import fetch_info


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

    if manager != "arch" and manager != "AUR":
        raise CommandException(manager)

    product_info = load_object(ProductInfo, product_info_raw)
    hash_update_str(hash, product_info.version)
    hash_update_str(hash, product_info.product_id)


async def fetch(
    settings: Settings,
    state: State,
    options: Options,
    package: Package,
    async_dependencies: AsyncIterable[Dependency],
    installation_path: Path | None,
    generators_path: Path | None,
) -> ProductIDAndInfo | AsyncIterable[str]:
    package_info = await fetch_info(package.name)

    dependencies = list[Dependency]()

    async for dependency in async_dependencies:
        dependencies.append(dependency)

    dependencies.sort(key=lambda dependency: (dependency.manager, dependency.name))

    product_id_hash = sha1()

    for dependency in dependencies:
        update_product_id_hash(product_id_hash, dependency)

    product_id = product_id_hash.hexdigest()
    product_info = ProductInfo(version=package_info.version, product_id=product_id)

    product_paths = state.product_paths

    product_key = f"{package.name}-{package.version}-{product_id}"

    if product_key not in product_paths:
        product_path_dir = Path(mkdtemp(dir=settings.cache_path))

        try:
            jinja_loader = Jinja2Environment(
                loader=Jinja2FileSystemLoader(state.data_path),
                autoescape=jinja2_select_autoescape(),
            )

            dockerfile_template = jinja_loader.get_template("Dockerfile.jinja")

            with (
                jinja_render_temp_file(
                    dockerfile_template,
                    {
                        "dependencies": chain(
                            (dependency.name for dependency in dependencies),
                            package_info.build_dependencies,
                        ),
                        "package": package.name,
                    },
                ) as dockerfile,
                TemporaryDirectory() as empty_directory,
            ):
                print(f"containerizer: {settings.containerizer}", file=stderr)
                print(f"dockerfile: {dockerfile.name}", file=stderr)
                print(f"empty_directory: {empty_directory}", file=stderr)
                process = await create_subprocess_exec(
                    "podman-remote",
                    "--url",
                    settings.containerizer,
                    "build",
                    "--quiet",
                    "--file",
                    dockerfile.name,
                    empty_directory,
                    stdin=DEVNULL,
                    stdout=PIPE,
                    stderr=None,
                )

                build_stdout = await asubprocess_communicate(
                    process, "Error in podman-remote build"
                )

            image_id = build_stdout.decode().strip()

            process = await create_subprocess_exec(
                "podman-remote",
                "--url",
                settings.containerizer,
                "create",
                image_id,
                stdin=DEVNULL,
                stdout=PIPE,
                stderr=DEVNULL,
            )

            create_stdout = await asubprocess_communicate(
                process, "Error in podman-remote create"
            )

            container_id = create_stdout.decode().strip()

            process = await create_subprocess_exec(
                "podman-remote",
                "--url",
                settings.containerizer,
                "cp",
                f"{container_id}:/workdir/product/.",
                product_path_dir,
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )

            await asubprocess_wait(process, CommandException())

            product_path = next(product_path_dir.iterdir())

            process = await create_subprocess_exec(
                "podman-remote",
                "--url",
                settings.containerizer,
                "rm",
                container_id,
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )

            await asubprocess_wait(process, CommandException())

            state.product_paths[product_key] = product_path
            state.product_paths.commit()
        except:
            product_path_dir.rmdir()
            raise

    return ProductIDAndInfo(product_id, product_info)
