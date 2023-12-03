from pathlib import Path

from PPpackage.main import main as PPpackage_main


async def PPpackage(
    debug: bool,
    do_update_database: bool,
    runner_path: Path,
    runner_workdirs_path: Path,
    cache_path: Path,
    generators_path: Path,
    destination_path: Path,
):
    await PPpackage_main(
        debug,
        do_update_database,
        runner_path,
        runner_workdirs_path,
        cache_path,
        generators_path,
        destination_path,
    )
