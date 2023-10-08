from asyncio import StreamReader, StreamWriter
from collections.abc import Iterable
from ctypes import string_at
from io import TextIOBase
from pathlib import Path
from sys import stderr


def pipe_read_line(debug, prefix, input: TextIOBase) -> str:
    line = input.readline().strip()

    if debug:
        print(f"DEBUG {prefix}: pipe read line: {line}", file=stderr)

    return line


def pipe_read_int(debug, prefix, input: TextIOBase) -> int:
    integer = int(pipe_read_line(debug, prefix, input))

    if debug:
        print(f"DEBUG {prefix}: pipe read int: {integer}", file=stderr)

    return integer


def pipe_read_string_maybe(debug, prefix, input: TextIOBase) -> str | None:
    length = pipe_read_int(debug, prefix, input)

    if debug:
        print(f"DEBUG {prefix}: pipe read string maybe length: {length}", file=stderr)

    if length < 0:
        return None

    string = input.read(length)

    if debug:
        print(f"DEBUG {prefix}: pipe read string maybe string: {string}", file=stderr)

    return string


def pipe_read_string(debug, prefix, input: TextIOBase) -> str:
    length = pipe_read_int(debug, prefix, input)

    if debug:
        print(f"DEBUG {prefix}: pipe read string length: {length}", file=stderr)

    string = input.read(length)

    if debug:
        print(f"DEBUG {prefix}: pipe read string string: {string}", file=stderr)

    return string


def pipe_read_strings(debug, prefix, input: TextIOBase) -> Iterable[str]:
    while True:
        string = pipe_read_string_maybe(debug, prefix, input)

        if debug:
            print(f"DEBUG {prefix}: pipe read strings string: {string}", file=stderr)

        if string is None:
            break

        yield string


def pipe_write_line(debug, prefix, output: TextIOBase, line: str) -> None:
    output.write(f"{line}\n")

    if debug:
        print(f"DEBUG {prefix}: pipe write line: {line}", file=stderr)


def pipe_write_int(debug, prefix, output: TextIOBase, integer: int) -> None:
    pipe_write_line(debug, prefix, output, str(integer))

    if debug:
        print(f"DEBUG {prefix}: pipe write int: {integer}", file=stderr)


def pipe_write_string(debug, prefix, output: TextIOBase, string: str) -> None:
    string_length = len(string)

    pipe_write_int(debug, prefix, output, string_length)

    if debug:
        print(f"DEBUG {prefix}: pipe write string length: {string_length}", file=stderr)

    output.write(string)

    if debug:
        print(f"DEBUG {prefix}: pipe write string string: {string}", file=stderr)


async def stream_read_line(debug, prefix, reader: StreamReader) -> str:
    line = (await reader.readline()).decode("ascii").strip()

    if debug:
        print(f"DEBUG {prefix}: stream read line: {line}", file=stderr)

    return line


async def stream_read_int(debug, prefix, reader: StreamReader) -> int:
    integer = int(await stream_read_line(debug, prefix, reader))

    if debug:
        print(f"DEBUG {prefix}: stream read int: {integer}", file=stderr)

    return integer


def stream_write_line(debug, prefix, writer: StreamWriter, line: str):
    writer.write(f"{line}\n".encode("ascii"))

    if debug:
        print(f"DEBUG {prefix}: stream write line: {line}", file=stderr)


def stream_write_int(debug, prefix, writer: StreamWriter, integer: int):
    stream_write_line(debug, prefix, writer, str(integer))

    if debug:
        print(f"DEBUG {prefix}: stream write int: {integer}", file=stderr)


async def stream_read_string_n(debug, prefix, reader: StreamReader, length: int) -> str:
    string = (await reader.read(length)).decode("ascii")

    if debug:
        print(f"DEBUG {prefix}: stream read string_n: {string}", file=stderr)

    return string


async def stream_read_string(debug, prefix, reader: StreamReader) -> str:
    length = await stream_read_int(debug, prefix, reader)

    if debug:
        print(f"DEBUG {prefix}: stream read string length: {length}", file=stderr)

    string = await stream_read_string_n(debug, prefix, reader, length)

    if debug:
        print(f"DEBUG {prefix}: stream read string string: {string}", file=stderr)

    return string


async def stream_read_string_maybe(debug, prefix, reader: StreamReader) -> str | None:
    length = await stream_read_int(debug, prefix, reader)

    if debug:
        print(f"DEBUG {prefix}: stream read string maybe length: {length}", file=stderr)

    if length < 0:
        return None

    string = await stream_read_string_n(debug, prefix, reader, length)

    if debug:
        print(f"DEBUG {prefix}: stream read string maybe string: {string}", file=stderr)

    return string


async def stream_read_strings(debug, prefix, reader: StreamReader):
    while True:
        string = await stream_read_string_maybe(debug, prefix, reader)

        if debug:
            print(f"DEBUG {prefix}: stream read strings string: {string}", file=stderr)

        if string is None:
            break

        yield string


async def stream_read_relative_path(debug, prefix, reader: StreamReader) -> Path:
    path = Path(await stream_read_string(debug, prefix, reader))

    if debug:
        print(f"DEBUG {prefix}: stream read path: {path}", file=stderr)

    if path.is_absolute():
        raise ValueError(f"Expected relative path, got {path}.")

    return path


def stream_write_string(debug, prefix, writer: StreamWriter, string: str):
    string_length = len(string)
    stream_write_int(debug, prefix, writer, string_length)

    if debug:
        print(
            f"DEBUG {prefix}: stream write string length: {string_length}", file=stderr
        )

    writer.write(string.encode("ascii"))

    if debug:
        print(f"DEBUG {prefix}: stream write string length: {string}", file=stderr)


def stream_write_strings(debug, prefix, writer: StreamWriter, strings):
    for string in strings:
        stream_write_string(debug, prefix, writer, string)

        if debug:
            print(
                f"DEBUG {prefix}: stream write strings string: {string}",
                file=stderr,
            )

    stream_write_int(debug, prefix, writer, -1)
