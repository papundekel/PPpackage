from collections.abc import Iterable
from io import TextIOBase

from .utils import MyException


def pipe_read_line_maybe(input: TextIOBase) -> str | None:
    line = input.readline()

    if len(line) == 0:
        return None

    return line.strip()


def pipe_read_line(input: TextIOBase) -> str:
    line = pipe_read_line_maybe(input)

    if line is None:
        raise MyException(f"Unexpected EOF.")

    return line


def pipe_read_int(input: TextIOBase) -> int:
    integer = int(pipe_read_line(input))

    return integer


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


def pipe_write_line(output: TextIOBase, line: str) -> None:
    output.write(f"{line}\n")


def pipe_write_int(output: TextIOBase, integer: int) -> None:
    pipe_write_line(output, str(integer))


def pipe_write_string(output: TextIOBase, string: str) -> None:
    string_length = len(string)

    pipe_write_int(output, string_length)

    output.write(string)
