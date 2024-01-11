from PPpackage_submanager.interface import Interface

from .fetch import fetch
from .install import install
from .lifespan import lifespan
from .resolve import resolve
from .settings import Settings

interface = Interface(
    Settings=Settings,
    Requirement=str,
    lifespan=lifespan,
    resolve=resolve,
    fetch=fetch,
    install=install,
)
