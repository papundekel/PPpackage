from collections.abc import Iterable, Mapping
from typing import Any

from pysat.formula import Formula

from PPpackage.translator.interface.interface import Interface
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import load_object

from .schemes import RequirementTranslatorConfig


class Translator:
    def __init__(
        self,
        config: RequirementTranslatorConfig,
    ):
        interface = load_interface_module(Interface, config.package)

        self.interface = interface
        self.parameters = load_object(interface.Parameters, config.parameters)

    async def translate_requirement(
        self, data: Mapping[str, Iterable[str]], requirement_unparsed: Any
    ) -> Formula:
        requirement = load_object(self.interface.Requirement, requirement_unparsed)

        return await self.interface.translate_requirement(
            self.parameters, data, requirement
        )


def Translators(
    translators_config: Mapping[str, RequirementTranslatorConfig]
) -> Mapping[str, Translator]:
    return {name: Translator(config) for name, config in translators_config.items()}
