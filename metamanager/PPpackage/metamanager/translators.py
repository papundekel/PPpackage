from asyncio import TaskGroup
from collections.abc import (
    AsyncIterable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
)
from typing import Any

from PPpackage.translator.interface.interface import Interface
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
        interface: Interface,
        parameters: Any,
        data: Mapping[str, Iterable[dict[str, str]]],
    ):
        self.interface = interface
        self.parameters = parameters
        self.data = data
        self.cache = dict[Any, list[str]]()

    @staticmethod
    async def create(
        repositories: Iterable[Repository], config: RequirementTranslatorConfig
    ):
        interface = load_interface_module(Interface, config.package)
        parameters = validate_python(interface.Parameters, config.parameters)

        data = await fetch_translator_data(repositories)

        return Translator(interface, parameters, data)

    def translate_requirement(self, requirement_unparsed: Any) -> Iterable[str]:
        requirement = validate_python(self.interface.Requirement, requirement_unparsed)

        translated_requirement = self.cache.get(requirement)

        if translated_requirement is None:
            translated_requirement = self.interface.translate_requirement(
                self.parameters, self.data, requirement
            )

            translated_requirement = list(translated_requirement)
            self.cache[requirement] = translated_requirement

        for symbol in translated_requirement:
            yield symbol


async def Translators(
    repositories: Iterable[Repository],
    translators_config: Mapping[str, RequirementTranslatorConfig],
) -> Mapping[str, Translator]:
    async with TaskGroup() as group:
        translators_tasks = {
            name: group.create_task(Translator.create(repositories, config))
            for name, config in translators_config.items()
        }

    return {name: task.result() for name, task in translators_tasks.items()}
