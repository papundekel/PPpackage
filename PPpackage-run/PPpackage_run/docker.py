from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL
from os import getgid, getuid
from pathlib import Path

from PPpackage_utils.utils import asubprocess_wait


async def PPpackage(
    debug: bool,
    do_update_database: bool,
    runner_path: Path,
    runner_workdirs_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
):
    process = await create_subprocess_exec(
        "docker",
        "run",
        "--rm",
        "--interactive",
        "--ulimit",
        "nofile=1024:1048576",
        "--mount",
        "type=bind,readonly,source=/etc/passwd,destination=/etc/passwd",
        "--mount",
        "type=bind,readonly,source=/etc/group,destination=/etc/group",
        "--user",
        f"{getuid()}:{getgid()}",
        "--mount",
        f"type=bind,source={runner_workdirs_path},destination=/mnt/PPpackage-runner",
        "--mount",
        f"type=bind,source={runner_path},destination=/run/PPpackage-runner.sock",
        "--mount",
        f"type=bind,source={cache_path},destination=/workdir/cache",
        "--mount",
        f"type=bind,source={generators_path},destination=/workdir/generators",
        "--mount",
        f"type=bind,source={destination_path},destination=/workdir/root",
        "fackop/pppackage",
        "python",
        "-m",
        "PPpackage",
        "--debug" if debug else "--no-debug",
        "--update-database" if do_update_database else "--no-update-database",
        "/run/PPpackage-runner.sock",
        "/mnt/PPpackage-runner",
        "/workdir/cache",
        "/workdir/generators",
        "/workdir/root",
        stdin=None,
        stdout=DEVNULL,
        stderr=None,
    )

    await asubprocess_wait(process, "Error in PPpackage")
