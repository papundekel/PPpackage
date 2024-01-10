from contextlib import asynccontextmanager

from .settings import Settings
from .utils import State, get_path


@asynccontextmanager
async def lifespan(settings: Settings):
    import PPpackage_conan

    from . import deployer

    data_path = get_path(PPpackage_conan).parent / "data"
    deployer_path = get_path(deployer)

    yield State(data_path, deployer_path)
