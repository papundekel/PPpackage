from PPpackage.translator.interface.interface import Interface

from .schemes import Parameters
from .translate_requirement import translate_requirement

interface = Interface(
    Parameters=Parameters,
    Requirement=str,
    translate_requirement=translate_requirement,
)
