from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Protocol

from PPpackage.generator.interface.interface import Interface
from PPpackage.utils.utils import load_interface_module
from PPpackage.utils.validation import validate_python

from .schemes import GeneratorConfig


class Generator:
    def __init__(self, config: GeneratorConfig):
        interface = load_interface_module(Interface, config.package)

        self.interface = interface
        self.parameters = validate_python(interface.Parameters, config.parameters)

    async def generate(
        self,
        generator_name: str,
        products: Iterable[tuple[str, Path]],
        output_path: Path,
    ) -> None:
        await self.interface.generate(
            self.parameters, generator_name, products, output_path
        )


class Pattern(Protocol):
    def match(self, string: str) -> bool: ...


class ExactPattern(Pattern):
    def __init__(self, value: str):
        self.value = value

    def match(self, string: str) -> bool:
        return string == self.value


class PrefixPattern(Pattern):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def match(self, string: str) -> bool:
        return string.startswith(self.prefix)


def create_pattern(pattern: str) -> Pattern:
    if pattern.endswith("*"):
        return PrefixPattern(pattern[:-1])
    else:
        return ExactPattern(pattern)


class Generators:
    def __init__(self, configs: Mapping[str, GeneratorConfig]):
        patterns_and_generators = list[tuple[Pattern, Generator]]()

        for pattern, config in configs.items():
            patterns_and_generators.append((create_pattern(pattern), Generator(config)))

        self.patterns_and_generators = patterns_and_generators

    async def generate(
        self,
        generator_name: str,
        products: Iterable[tuple[str, Path]],
        output_path: Path,
    ) -> None:
        for pattern, generator in self.patterns_and_generators:
            if pattern.match(generator_name):
                await generator.generate(generator_name, products, output_path)
                return

        raise Exception(f"Generator {generator_name} did not match any pattern.")
