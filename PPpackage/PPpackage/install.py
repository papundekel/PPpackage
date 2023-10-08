from asyncio import (
    StreamReader,
    StreamWriter,
    create_subprocess_exec,
    open_unix_connection,
)
from asyncio.subprocess import DEVNULL, PIPE
from collections.abc import Mapping
from contextlib import asynccontextmanager
from functools import partial
from io import TextIOWrapper
from pathlib import Path
from random import choices as random_choices
from sys import stderr

from PPpackage_utils.io import (
    pipe_read_line,
    pipe_read_string,
    pipe_read_strings,
    pipe_write_int,
    pipe_write_string,
    stream_read_int,
    stream_write_line,
    stream_write_string,
    stream_write_strings,
)
from PPpackage_utils.utils import (
    MyException,
    TemporaryPipe,
    asubprocess_communicate,
    json_dumps,
)

from .sub import install as PP_install


def merge_lockfiles(
    versions: Mapping[str, str], product_ids: Mapping[str, str]
) -> Mapping[str, Mapping[str, str]]:
    return {
        package: {"version": versions[package], "product_id": product_ids[package]}
        for package in versions.keys() & product_ids.keys()
    }


async def install_manager_command(
    debug: bool,
    pipe_to_sub: TextIOWrapper,
    pipe_from_sub: TextIOWrapper,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
):
    stream_write_line(debug, "PPpackage", daemon_writer, "COMMAND")
    stream_write_string(
        debug, "PPpackage", daemon_writer, str(destination_relative_path)
    )

    command = pipe_read_string(debug, "PPpackage", pipe_from_sub)
    stream_write_string(debug, "PPpackage", daemon_writer, command)

    args = pipe_read_strings(debug, "PPpackage", pipe_from_sub)
    stream_write_strings(debug, "PPpackage", daemon_writer, args)

    with TemporaryPipe(daemon_workdir_path) as pipe_hook_path:
        pipe_write_string(debug, "PPpackage", pipe_to_sub, str(pipe_hook_path))
        pipe_to_sub.flush()

        stream_write_string(
            debug,
            "PPpackage",
            daemon_writer,
            str(pipe_hook_path.relative_to(daemon_workdir_path)),
        )

        await daemon_writer.drain()

        return_value = await stream_read_int(debug, "PPpackage", daemon_reader)

        pipe_write_int(debug, "PPpackage", pipe_to_sub, return_value)
        pipe_to_sub.flush()


async def install_external_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    with TemporaryPipe() as pipe_from_sub_path, TemporaryPipe() as pipe_to_sub_path:
        if debug:
            print(
                f"DEBUG PPpackage: {manager} pipe_from_sub_path: {pipe_from_sub_path}, pipe_to_sub_path: {pipe_to_sub_path}",
                file=stderr,
            )

        process_creation = create_subprocess_exec(
            f"PPpackage-{manager}",
            "--debug" if debug else "--no-debug",
            "install",
            str(cache_path),
            str(daemon_workdir_path / destination_relative_path),
            str(pipe_from_sub_path),
            str(pipe_to_sub_path),
            stdin=PIPE,
            stdout=DEVNULL,
            stderr=None,
        )

        products = merge_lockfiles(versions, product_ids)

        indent = 4 if debug else None

        products_json = json_dumps(products, indent=indent)

        if debug:
            print(f"DEBUG PPpackage: sending to {manager}'s install:", file=stderr)
            print(products_json, file=stderr)

        products_json_bytes = products_json.encode("ascii")

        process = await process_creation

        if process.stdin is None:
            raise MyException(f"Error in {manager}'s install.")

        process.stdin.write(products_json_bytes)
        process.stdin.close()
        await process.stdin.wait_closed()

        if debug:
            print(f"DEBUG PPpackage: closed sub's stdin", file=stderr)

        with open(pipe_from_sub_path, "r", encoding="ascii") as pipe_from_sub:
            with open(pipe_to_sub_path, "w", encoding="ascii") as pipe_to_sub:
                while True:
                    header = pipe_read_line(debug, "PPpackage", pipe_from_sub)

                    if header == "END":
                        break
                    elif header == "COMMAND":
                        await install_manager_command(
                            debug,
                            pipe_to_sub,
                            pipe_from_sub,
                            daemon_reader,
                            daemon_writer,
                            daemon_workdir_path,
                            destination_relative_path,
                        )
                    else:
                        raise MyException(
                            f"Invalid hook header from {manager} `{header}`."
                        )

        await asubprocess_communicate(
            process,
            f"Error in {manager}'s install.",
            None,
        )


async def install_manager(
    debug: bool,
    manager: str,
    cache_path: Path,
    daemon_reader: StreamReader,
    daemon_writer: StreamWriter,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    versions: Mapping[str, str],
    product_ids: Mapping[str, str],
) -> None:
    if manager == "PP":
        installer = partial(
            PP_install,
            destination_path=daemon_workdir_path / destination_relative_path,
        )
    else:
        installer = partial(
            install_external_manager,
            manager=manager,
            daemon_reader=daemon_reader,
            daemon_writer=daemon_writer,
            daemon_workdir_path=daemon_workdir_path,
            destination_relative_path=destination_relative_path,
        )

    await installer(
        debug=debug,
        cache_path=cache_path,
        versions=versions,
        product_ids=product_ids,
    )


def generate_machine_id(machine_id_path: Path):
    if machine_id_path.exists():
        return

    machine_id_path.parent.mkdir(exist_ok=True, parents=True)

    with machine_id_path.open("w") as machine_id_file:
        machine_id_file.write(
            "".join(random_choices([str(digit) for digit in range(10)], k=32)) + "\n"
        )


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id


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


machine_id_relative_path = Path("etc") / "machine-id"


async def install(
    debug: bool,
    cache_path: Path,
    daemon_socket_path: Path,
    daemon_workdir_path: Path,
    destination_relative_path: Path,
    meta_versions: Mapping[str, Mapping[str, str]],
    meta_product_ids: Mapping[str, Mapping[str, str]],
) -> None:
    generate_machine_id(
        daemon_workdir_path / destination_relative_path / machine_id_relative_path
    )

    machine_id = read_machine_id(Path("/") / machine_id_relative_path)

    async with communicate_with_daemon(debug, daemon_socket_path) as (
        daemon_reader,
        daemon_writer,
    ):
        stream_write_string(debug, "PPpackage", daemon_writer, machine_id)

        for manager, versions in meta_versions.items():
            product_ids = meta_product_ids[manager]

            await install_manager(
                debug,
                manager,
                cache_path,
                daemon_reader,
                daemon_writer,
                daemon_workdir_path,
                destination_relative_path,
                versions,
                product_ids,
            )
