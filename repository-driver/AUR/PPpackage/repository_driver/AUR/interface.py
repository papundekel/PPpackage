from types import NoneType

from PPpackage.repository_driver.interface.interface import Interface

from .compute_product_info import compute_product_info
from .fetch_translator_data import fetch_translator_data
from .get_epoch import get_epoch
from .get_formula import get_formula
from .get_package_detail import get_package_detail
from .schemes import DriverParameters, RepositoryParameters
from .translate_options import translate_options

interface = Interface(
    DriverParameters=DriverParameters,
    RepositoryParameters=RepositoryParameters,
    TranslatedOptions=NoneType,
    get_epoch=get_epoch,
    fetch_translator_data=fetch_translator_data,
    translate_options=translate_options,
    get_formula=get_formula,
    get_package_detail=get_package_detail,
    compute_product_info=compute_product_info,
)
