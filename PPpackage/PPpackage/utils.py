from asyncio import open_unix_connection
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from PPpackage_utils.io import stream_write_line
from PPpackage_utils.parse import GenerateInputPackagesValue

machine_id_relative_path = Path("etc") / "machine-id"


@asynccontextmanager
async def communicate_with_daemon(
    debug: bool,
    daemon_path: Path,
):
    (
        daemon_reader,
        daemon_writer,
    ) = await open_unix_connection(daemon_path)

    try:
        yield daemon_reader, daemon_writer
    finally:
        stream_write_line(debug, "PPpackage", daemon_writer, "END")
        await daemon_writer.drain()
        daemon_writer.close()
        await daemon_writer.wait_closed()


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id
