from PPpackage.generator.interface.interface import Interface

from .generate import generate
from .schemes import Parameters

interface = Interface(Parameters=Parameters, generate=generate)
