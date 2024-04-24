from collections.abc import Mapping
from pathlib import Path
from sys import stderr

from PPpackage.installer.interface.interface import Interface
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_object

from .schemes import InstallerConfig


class Installer:
    def __init__(
        self,
        config: InstallerConfig,
    ):
        interface = load_interface_module(Interface, config.package)

        self.interface = interface
        self.parameters = load_object(interface.Parameters, config.parameters)

    async def install(self, product_path: Path, installation_path: Path) -> None:
        print(f"Installing {product_path}...", file=stderr)
        await self.interface.install(self.parameters, product_path, installation_path)


def Installers(
    translators_config: Mapping[str, InstallerConfig]
) -> Mapping[str, Installer]:
    return {name: Installer(config) for name, config in translators_config.items()}
