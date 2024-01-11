from PPpackage_submanager.interface import Interface

from .fetch import fetch
from .generate import generate
from .install import install
from .lifespan import lifespan
from .resolve import resolve
from .schemes import Requirement
from .settings import Settings

interface = Interface(
    Settings=Settings,
    Requirement=Requirement,
    lifespan=lifespan,
    resolve=resolve,
    fetch=fetch,
    install=install,
    generate=generate,
)
