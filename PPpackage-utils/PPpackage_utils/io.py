from asyncio import StreamReader, StreamWriter
from collections.abc import Iterable
from io import TextIOBase
from pathlib import Path


def pipe_read_line(input: TextIOBase) -> str:
    return input.readline().strip()


def pipe_read_int(input: TextIOBase) -> int:
    return int(pipe_read_line(input))


def pipe_read_string_maybe(input: TextIOBase) -> str | None:
    length = pipe_read_int(input)

    if length < 0:
        return None

    string = input.read(length)

    return string


def pipe_read_string(input: TextIOBase) -> str:
    length = pipe_read_int(input)

    string = input.read(length)

    return string


def pipe_read_strings(input: TextIOBase) -> Iterable[str]:
    while True:
        string = pipe_read_string_maybe(input)

        if string is None:
            break

        yield string


def pipe_write_int(output: TextIOBase, integer: int) -> None:
    output.write(f"{integer}\n")


def pipe_write_string(output: TextIOBase, string: str) -> None:
    pipe_write_int(output, len(string))
    output.write(string)


async def stream_read_line(reader: StreamReader) -> str:
    return (await reader.readline()).decode("ascii").strip()


async def stream_read_int(reader: StreamReader) -> int:
    return int(await stream_read_line(reader))


def stream_write_line(writer: StreamWriter, line: str):
    writer.write(f"{line}\n".encode("ascii"))


def stream_write_int(writer: StreamWriter, integer: int):
    stream_write_line(writer, str(integer))


async def stream_read_string_n(reader: StreamReader, length: int) -> str:
    return (await reader.read(length)).decode("ascii")


async def stream_read_string(reader: StreamReader) -> str:
    length = await stream_read_int(reader)
    return await stream_read_string_n(reader, length)


async def stream_read_string_maybe(reader: StreamReader) -> str | None:
    length = await stream_read_int(reader)

    if length < 0:
        return None

    return await stream_read_string_n(reader, length)


async def stream_read_strings(reader: StreamReader):
    while True:
        string = await stream_read_string_maybe(reader)

        if string is None:
            break

        yield string


async def stream_read_relative_path(reader: StreamReader) -> Path:
    path = Path(await stream_read_string(reader))

    if path.is_absolute():
        raise ValueError(f"Expected relative path, got {path}.")

    return path


def stream_write_string(writer: StreamWriter, string: str):
    stream_write_int(writer, len(string))
    writer.write(string.encode("ascii"))


def stream_write_strings(writer: StreamWriter, strings):
    for string in strings:
        stream_write_string(writer, string)
    stream_write_int(writer, -1)
