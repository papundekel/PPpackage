from types import NoneType

from PPpackage.repository_driver.interface.interface import Interface

from .fetch_packages import fetch_packages
from .schemes import DriverParameters, RepositoryParameters
from .translate_options import translate_options

interface = Interface(
    DriverParameters=DriverParameters,
    RepositoryParameters=RepositoryParameters,
    TranslatedOptions=NoneType,
    translate_options=translate_options,
    fetch_packages=fetch_packages,
)
