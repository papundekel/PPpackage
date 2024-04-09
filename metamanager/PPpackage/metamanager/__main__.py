from logging import Formatter as LoggingFormatter
from logging import LogRecord
from logging import StreamHandler as StreamLoggingHandler
from logging import getLogger
from pathlib import Path
from typing import Optional

from typer import Option as TyperOption
from typing_extensions import Annotated

from PPpackage.utils.cli import AsyncTyper, run

from .main import main

app = AsyncTyper()


class LoggingFilter:
    def filter(self, record: LogRecord) -> bool:
        return record.name.startswith("PPpackage") or record.name.startswith("httpx")


logging_formatter = LoggingFormatter("%(name)s: %(message)s")
logging_handler = StreamLoggingHandler()
logging_handler.setLevel("DEBUG")
logging_handler.addFilter(LoggingFilter())
logging_handler.setFormatter(logging_formatter)
logger = getLogger()
logger.setLevel("DEBUG")
logger.addHandler(logging_handler)


@app.command()
async def main_command(
    destination_path: Path,
    config_path: Annotated[Path, TyperOption("--config")],
    workdir_path: Annotated[Path, TyperOption("--workdir")] = Path("/tmp"),
    generators_path: Annotated[Optional[Path], TyperOption("--generators")] = None,
    graph_path: Annotated[Optional[Path], TyperOption("--graph")] = None,
) -> None:
    await main(
        workdir_path,
        config_path,
        destination_path,
        generators_path,
        graph_path,
    )


run(app, "PPpackage")
