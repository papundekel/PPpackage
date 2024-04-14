from pathlib import Path
from sys import stderr

from PPpackage.installer.interface.interface import Interface

from .schemes import Parameters


async def install(
    parameters: Parameters, product_path: Path, installation_path: Path
) -> None:
    print(f"Installing {product_path} to {installation_path}.", file=stderr)


interface = Interface(Parameters=Parameters, install=install)
