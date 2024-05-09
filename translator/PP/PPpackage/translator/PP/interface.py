from PPpackage.translator.interface.interface import Interface

from .get_assumptions import get_assumptions
from .schemes import Parameters
from .translate_requirement import translate_requirement

interface = Interface(
    Parameters=Parameters,
    Requirement=str,
    get_assumptions=get_assumptions,
    translate_requirement=translate_requirement,
)
