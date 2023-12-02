from asyncio import open_unix_connection
from collections.abc import Iterable
from contextlib import asynccontextmanager
from io import TextIOBase
from pathlib import Path
from sys import stderr

from PPpackage_utils.parse import dump_one
from PPpackage_utils.utils import MyException, RunnerRequestType

_DEBUG = False


def pipe_read_line_maybe(debug, prefix, input: TextIOBase) -> str | None:
    line = input.readline()

    if len(line) == 0:
        return None

    return line.strip()


def pipe_read_line(debug, prefix, input: TextIOBase) -> str:
    line = pipe_read_line_maybe(debug, prefix, input)

    if line is None:
        raise MyException(f"Unexpected EOF.")

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read line: {line}", file=stderr)

    return line


def pipe_read_int(debug, prefix, input: TextIOBase) -> int:
    integer = int(pipe_read_line(debug, prefix, input))

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read int: {integer}", file=stderr)

    return integer


def pipe_read_string_maybe(debug, prefix, input: TextIOBase) -> str | None:
    length = pipe_read_int(debug, prefix, input)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read string maybe length: {length}", file=stderr)

    if length < 0:
        return None

    string = input.read(length)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read string maybe string: {string}", file=stderr)

    return string


def pipe_read_string(debug, prefix, input: TextIOBase) -> str:
    length = pipe_read_int(debug, prefix, input)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read string length: {length}", file=stderr)

    string = input.read(length)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe read string string: {string}", file=stderr)

    return string


def pipe_read_strings(debug, prefix, input: TextIOBase) -> Iterable[str]:
    while True:
        string = pipe_read_string_maybe(debug, prefix, input)

        if _DEBUG:
            print(f"DEBUG {prefix}: pipe read strings string: {string}", file=stderr)

        if string is None:
            break

        yield string


def pipe_write_line(debug, prefix, output: TextIOBase, line: str) -> None:
    output.write(f"{line}\n")

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe write line: {line}", file=stderr)


def pipe_write_int(debug, prefix, output: TextIOBase, integer: int) -> None:
    pipe_write_line(debug, prefix, output, str(integer))

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe write int: {integer}", file=stderr)


def pipe_write_string(debug, prefix, output: TextIOBase, string: str) -> None:
    string_length = len(string)

    pipe_write_int(debug, prefix, output, string_length)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe write string length: {string_length}", file=stderr)

    output.write(string)

    if _DEBUG:
        print(f"DEBUG {prefix}: pipe write string string: {string}", file=stderr)


@asynccontextmanager
async def communicate_with_runner(
    debug: bool,
    daemon_path: Path,
    machine_id: str,
):
    (
        daemon_reader,
        daemon_writer,
    ) = await open_unix_connection(daemon_path)

    try:
        await dump_one(debug, daemon_writer, machine_id)
        yield daemon_reader, daemon_writer
    finally:
        await dump_one(debug, daemon_writer, RunnerRequestType.END)
        daemon_writer.close()
        await daemon_writer.wait_closed()
