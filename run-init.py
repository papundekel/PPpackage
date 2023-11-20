#!/usr/bin/env python

from asyncio import run
from pathlib import Path
from sys import argv

from PPpackage_utils.io import communicate_with_daemon
from PPpackage_utils.parse import model_dump_stream, model_validate_stream
from PPpackage_utils.utils import RunnerRequestType


async def main():
    runner_path = Path(argv[1])
    machine_id = argv[2]
    debug = argv[3] == "--debug"

    async with communicate_with_daemon(debug, runner_path) as (reader, writer):
        await model_dump_stream(debug, writer, machine_id)
        await model_dump_stream(debug, writer, RunnerRequestType.INIT)

        workdir_relative_path = await model_validate_stream(debug, reader, Path)

    print(workdir_relative_path, end=None)


run(main())
