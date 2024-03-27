from logging import Formatter as LoggingFormatter
from logging import LogRecord
from logging import StreamHandler as StreamLoggingHandler
from logging import getLogger

from PPpackage_submanager.interface import Interface

from .fetch import fetch
from .install import install
from .lifespan import lifespan
from .resolve import resolve
from .settings import Settings


class LoggingFilter:
    def filter(self, record: LogRecord) -> bool:
        return record.name.startswith("PPpackage_PP") or record.name.startswith(
            "PPpackage_submanager"
        )


logging_formatter = LoggingFormatter("PP: %(name)s: %(message)s")
logging_handler = StreamLoggingHandler()
logging_handler.setLevel("DEBUG")
logging_handler.addFilter(LoggingFilter())
logging_handler.setFormatter(logging_formatter)
logger = getLogger()
logger.setLevel("DEBUG")
logger.addHandler(logging_handler)

interface = Interface(
    Settings=Settings,
    Requirement=str,
    lifespan=lifespan,
    resolve=resolve,
    fetch=fetch,
    install=install,
)
