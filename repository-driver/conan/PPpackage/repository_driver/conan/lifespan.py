from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from utils.utils import get_module_path

from .settings import Settings


@dataclass(frozen=True)
class State:
    data_path: Path
    deployer_path: Path


@asynccontextmanager
async def lifespan(settings: Settings):
    import conan

    from . import deployer

    data_path = get_module_path(conan).parent / "data"
    deployer_path = get_module_path(deployer)

    yield State(data_path, deployer_path)
