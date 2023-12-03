from asyncio import run as asyncio_run
from collections.abc import Callable
from contextlib import contextmanager
from multiprocessing import Process
from os import environ
from pathlib import Path

from PPpackage_runner.main import main as runner_main
from PPpackage_utils.submanager import AsyncTyper, run
from PPpackage_utils.utils import MyException, TemporaryDirectory, ensure_dir_exists


def runner(debug: bool, run_path: Path, runner_workdirs_path: Path):
    asyncio_run(runner_main(debug, run_path, runner_workdirs_path))


@contextmanager
def process_lifetime(target: Callable, *args):
    process = Process(target=target, args=args)
    process.start()

    try:
        yield
    finally:
        process.terminate()
        process.join()


app = AsyncTyper()


@app.command()
async def main_command(
    mode: str,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
    update_database: bool = False,
    debug: bool = False,
):
    if mode == "docker":
        from .docker import PPpackage
    elif mode == "native":
        from .native import PPpackage
    else:
        raise MyException(f"Invalid mode: {mode}")

    run_path = Path(environ["XDG_RUNTIME_DIR"])

    ensure_dir_exists(cache_path)
    ensure_dir_exists(generators_path)
    ensure_dir_exists(destination_path)

    with TemporaryDirectory() as runner_workdirs_path:
        with process_lifetime(runner, debug, run_path, runner_workdirs_path):
            runner_path = run_path / "PPpackage-runner.sock"

            await PPpackage(
                debug,
                update_database,
                runner_path,
                runner_workdirs_path,
                cache_path,
                generators_path,
                destination_path,
            )


run(app, "PPpackage-run")
