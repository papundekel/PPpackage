from pathlib import Path

from PPpackage_utils.submanager import AsyncTyper, run

from .main import main, program_name

app = AsyncTyper()


@app.command()
async def main_command(run_path: Path, workdirs_path: Path, debug: bool = False):
    await main(debug, run_path, workdirs_path)


run(app, program_name)
