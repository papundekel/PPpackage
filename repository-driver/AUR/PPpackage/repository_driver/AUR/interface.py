from types import NoneType

from PPpackage.repository_driver.interface.interface import Interface

from .fetch_formula import fetch_formula
from .fetch_packages import fetch_packages
from .get_epoch import get_epoch
from .schemes import DriverParameters, RepositoryParameters
from .translate_options import translate_options

interface = Interface(
    DriverParameters=DriverParameters,
    RepositoryParameters=RepositoryParameters,
    TranslatedOptions=NoneType,
    get_epoch=get_epoch,
    fetch_packages=fetch_packages,
    translate_options=translate_options,
    fetch_formula=fetch_formula,
)
