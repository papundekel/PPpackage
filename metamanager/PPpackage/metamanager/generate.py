from asyncio import TaskGroup
from collections.abc import Iterable, Mapping
from pathlib import Path

from networkx import MultiDiGraph

from metamanager.PPpackage.metamanager.graph import get_graph_items

from .generator import Generators
from .schemes import GeneratorConfig


async def generate(
    configs: Mapping[str, GeneratorConfig],
    graph: MultiDiGraph,
    generator_names: Iterable[str],
    output_path: Path,
) -> None:
    generators = Generators(configs)

    products = [
        (package, (await data["product"])[0])
        for package, data in get_graph_items(graph)
    ]

    output_path.mkdir(parents=True, exist_ok=True)

    async with TaskGroup() as task_group:
        for generator_name in generator_names:
            task_group.create_task(
                generators.generate(generator_name, products, output_path)
            )
