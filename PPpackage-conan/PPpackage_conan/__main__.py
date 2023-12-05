from pathlib import Path

from PPpackage_utils.submanager import AsyncTyper, run

from .main import PROGRAM_NAME, main

app = AsyncTyper()


@app.command()
async def main_commmand(
    run_path: Path,
    cache_path: Path,
    debug: bool = False,
):
    await main(debug, run_path, cache_path)


run(app, PROGRAM_NAME)
