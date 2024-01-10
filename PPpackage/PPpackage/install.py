from collections.abc import Iterable, Mapping
from pathlib import Path
from sys import stderr

from PPpackage_submanager.schemes import ManagerAndName

from PPpackage.submanager import Submanager

from .utils import NodeData, data_to_product


async def install(
    submanagers: Mapping[str, Submanager],
    order: Iterable[tuple[ManagerAndName, NodeData]],
    installation_path: Path,
) -> None:
    stderr.write(f"Installing packages...\n")

    previous_submanager: Submanager | None = None
    ids = dict[str, int]()

    for node, data in order:
        submanager = submanagers[node.manager]

        if previous_submanager is None:
            id = await submanager.install_init(installation_path)
            ids[submanager.name] = id
        elif previous_submanager.name != submanager.name:
            previous_id = ids[previous_submanager.name]
            id = ids.get(submanager.name)
            id = await previous_submanager.install_send(previous_id, submanager, id)
        else:
            id = ids[submanager.name]

        await submanager.install(
            id, installation_path, data_to_product(node.name, data)
        )

        previous_submanager = submanager

    for submanager_name, id in ids.items():
        await submanagers[submanager_name].install_delete(id)
