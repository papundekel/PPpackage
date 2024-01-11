from importlib import import_module
from sys import argv
from typing import cast as type_cast

from PPpackage_submanager.interface import Interface


def import_interface(package: str) -> Interface:
    return type_cast(
        Interface,
        import_module(f"{package}.interface").interface,
    )


package1 = argv[1]
package2 = argv[2]

interface1 = import_interface(package1)
interface2 = import_interface(package2)

print(interface1.Settings)
print(interface2.Settings)
