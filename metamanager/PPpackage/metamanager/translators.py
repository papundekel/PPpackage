from asyncio import TaskGroup
from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence
from itertools import chain
from typing import Any

from PPpackage.translator.interface.interface import Interface
from PPpackage.translator.interface.schemes import Literal
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import validate_python

from .repository import Repository
from .schemes import RequirementTranslatorConfig


async def repository_fetch_translator_data(
    repository: Repository,
    translator_info: MutableMapping[str, MutableSequence[dict[str, str]]],
):
    async for info in repository.fetch_translator_data():
        translator_info.setdefault(info.group, []).append(info.symbol)


async def fetch_translator_data(
    repositories: Iterable[Repository],
) -> Mapping[str, Iterable[dict[str, str]]]:
    translator_info = dict[str, MutableSequence[dict[str, str]]]()

    async with TaskGroup() as group:
        for repository in repositories:
            group.create_task(
                repository_fetch_translator_data(repository, translator_info)
            )

    return translator_info


class Translator:
    def __init__(
        self,
        config: RequirementTranslatorConfig,
        data: Mapping[str, Iterable[dict[str, str]]],
    ):
        interface = load_interface_module(Interface, config.package)
        parameters = validate_python(interface.Parameters, config.parameters)

        self.interface = interface
        self.parameters = parameters
        self.data = data
        self.cache = dict[Any, list[str]]()

    def translate_requirement(self, requirement_unparsed: Any) -> Iterable[str]:
        requirement = validate_python(self.interface.Requirement, requirement_unparsed)

        translated_requirement = self.cache.get(requirement)

        if translated_requirement is None:
            translated_requirement = self.interface.translate_requirement(
                self.parameters, self.data, requirement
            )

            translated_requirement_list = list[str]()

            for symbol in translated_requirement:
                translated_requirement_list.append(symbol)
                yield symbol

            self.cache[requirement] = translated_requirement_list
        else:
            yield from translated_requirement

    def get_assumptions(self) -> Iterable[Literal]:
        return self.interface.get_assumptions(self.parameters, self.data)


async def Translators(
    repositories: Iterable[Repository],
    translators_config: Mapping[str, RequirementTranslatorConfig],
) -> tuple[Mapping[str, Translator], Iterable[Literal]]:
    data = await fetch_translator_data(repositories)

    translators = {
        name: Translator(config, data) for name, config in translators_config.items()
    }

    assumptions = set(
        chain.from_iterable(
            translator.get_assumptions() for translator in translators.values()
        )
    )

    return translators, assumptions
