from importlib import import_module
from typing import cast as type_cast


def load_interface_module[T](_: type[T], package_name: str) -> T:
    return type_cast(T, import_module(f"{package_name}.interface").interface)
