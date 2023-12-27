from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from contextlib import contextmanager
from dataclasses import dataclass
from json import dump as json_dump
from json import load as json_load
from pathlib import Path

from PPpackage_runner.database import TokenDB, User, UserDB
from PPpackage_runner.settings import DEBUG
from PPpackage_utils.server import Framework
from PPpackage_utils.server import State as BaseState
from PPpackage_utils.utils import asubprocess_wait


@dataclass(frozen=True)
class State(BaseState):
    bundle_path: Path
    crun_root_path: Path


framework = Framework(State, TokenDB, User, UserDB)


@contextmanager
def edit_json_file(debug: bool, path: Path):
    with path.open("r+") as file:
        data = json_load(file)

        try:
            yield data
        finally:
            file.seek(0)
            file.truncate()

            json_dump(data, file, indent=4 if debug else None)


CONFIG_RELATIVE_PATH = Path("config.json")


def edit_config(bundle_path: Path):
    return edit_json_file(DEBUG, bundle_path / CONFIG_RELATIVE_PATH)


async def create_config(bundle_path: Path):
    process_creation = create_subprocess_exec(
        "crun",
        "spec",
        "--rootless",
        cwd=bundle_path,
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )

    await asubprocess_wait(await process_creation, Exception("Error in `crun spec`."))

    with edit_config(bundle_path) as config:
        config["process"]["terminal"] = False
        config["root"]["readonly"] = False
