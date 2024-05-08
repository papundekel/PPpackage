from PPpackage.translator.interface.interface import Interface

from .schemes import ExcludeRequirement, Parameters
from .translate_requirement import translate_requirement

interface = Interface(
    Parameters=Parameters,
    Requirement=str | ExcludeRequirement,  # type: ignore
    translate_requirement=translate_requirement,
)
