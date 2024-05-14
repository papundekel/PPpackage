from PPpackage.translator.interface.interface import Interface

from .get_assumptions import get_assumptions
from .schemes import Parameters, Requirement
from .translate_requirement import translate_requirement

interface = Interface(
    Parameters=Parameters,
    Requirement=Requirement,
    get_assumptions=get_assumptions,
    translate_requirement=translate_requirement,
)
