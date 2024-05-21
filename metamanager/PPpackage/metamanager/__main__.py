from logging import Formatter as LoggingFormatter
from logging import LogRecord
from logging import StreamHandler as StreamLoggingHandler
from logging import getLogger
from pathlib import Path
from typing import Optional

from typer import Option as TyperOption
from typing_extensions import Annotated

from PPpackage.utils.cli import App

from .main import main

app = App()


class LoggingFilter:
    def filter(self, record: LogRecord) -> bool:
        return record.name.startswith("PPpackage")


logging_formatter = LoggingFormatter("%(name)s: %(message)s")
logging_handler = StreamLoggingHandler()
logging_handler.setLevel("INFO")
logging_handler.addFilter(LoggingFilter())
logging_handler.setFormatter(logging_formatter)
logger = getLogger()
logger.setLevel("INFO")
logger.addHandler(logging_handler)


@app.command()
async def main_command(
    installation_path: Path,
    config_path: Annotated[Path, TyperOption("--config")],
    generators_path: Annotated[Optional[Path], TyperOption("--generators")] = None,
    graph_path: Annotated[Optional[Path], TyperOption("--graph")] = None,
) -> None:
    await main(config_path, installation_path, generators_path, graph_path)


app()
