from collections.abc import Mapping
from typing import Any

from PPpackage.repository_driver.interface.interface import Interface

from .compute_product_info import compute_product_info
from .discover_packages import discover_packages
from .get_epoch import get_epoch
from .get_formula import get_formula
from .get_package_detail import get_package_detail
from .schemes import ConanOptions, DriverParameters, RepositoryParameters
from .translate_options import translate_options

interface = Interface(
    DriverParameters=DriverParameters,
    RepositoryParameters=RepositoryParameters,
    TranslatedOptions=ConanOptions,
    get_epoch=get_epoch,
    translate_options=translate_options,
    discover_packages=discover_packages,
    get_formula=get_formula,
    get_package_detail=get_package_detail,
    compute_product_info=compute_product_info,
)
