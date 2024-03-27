from collections.abc import Iterable, Mapping
from logging import getLogger
from pathlib import Path
from sys import stderr

from PPpackage_submanager.schemes import ManagerAndName, Product
from PPpackage_utils.utils import ensure_dir_exists

from PPpackage.submanager import Submanager

from .utils import NodeData, data_to_product

logger = getLogger(__name__)


async def install_manager(
    submanager: Submanager, id: str, installation_path: Path, product: Product
) -> None:
    stderr.write(f"\t{submanager.name}: ")

    await submanager.install(id, installation_path, product)

    stderr.write(f"{product.name}\n")


async def install(
    submanagers: Mapping[str, Submanager],
    order: Iterable[tuple[ManagerAndName, NodeData]],
    destination_path: Path,
) -> None:
    stderr.write(f"Installing packages...\n")

    ensure_dir_exists(destination_path)

    previous_submanager: Submanager | None = None
    ids = dict[str, str]()

    for node, data in order:
        logger.info(f"Installing {node.manager} {node.name}...")

        submanager = submanagers[node.manager]

        if previous_submanager is None:
            id = await submanager.install_init(destination_path)
            ids[submanager.name] = id
        elif previous_submanager.name != submanager.name:
            previous_id = ids[previous_submanager.name]
            id = ids.get(submanager.name)

            logger.info(
                f"Sending installation {previous_id} "
                f"from {previous_submanager.name} to {submanager.name}..."
            )
            id = await previous_submanager.install_send(
                previous_id, submanager, id, destination_path
            )
            logger.info(f"Sent installation {previous_id} to {id}.")

            ids[submanager.name] = id
        else:
            id = ids[submanager.name]

        await install_manager(
            submanager, id, destination_path, data_to_product(node.name, data)
        )

        previous_submanager = submanager

        logger.info(f"Installed {node.manager} {node.name}.")

    if previous_submanager is not None:
        id = ids[previous_submanager.name]
        logger.info(f"Downloading installation {id}...")
        await previous_submanager.install_download(id, destination_path)
        logger.info(f"Downloaded installation {id}.")

    for submanager_name, id in ids.items():
        await submanagers[submanager_name].install_delete(id)

    stderr.write(f"Installation done.\n")
