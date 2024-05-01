from PPpackage.installer.interface.interface import Interface

from .install import install
from .schemes import Parameters

interface = Interface(Parameters=Parameters, install=install)
