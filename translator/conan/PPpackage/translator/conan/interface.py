from PPpackage.translator.interface.interface import Interface

from .schemes import Parameters, Requirement
from .translate_requirement import translate_requirement

interface = Interface(
    Parameters=Parameters,
    Requirement=Requirement,
    translate_requirement=translate_requirement,
)
