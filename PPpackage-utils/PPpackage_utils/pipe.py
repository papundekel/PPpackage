from collections.abc import Iterable
from io import TextIOBase
from sys import stderr

from PPpackage_utils.utils import MyException


def pipe_read_line_maybe(prefix, input: TextIOBase) -> str | None:
    line = input.readline()

    if len(line) == 0:
        return None

    return line.strip()


def pipe_read_line(prefix, input: TextIOBase) -> str:
    line = pipe_read_line_maybe(prefix, input)

    if line is None:
        raise MyException(f"Unexpected EOF.")

    return line


def pipe_read_int(prefix, input: TextIOBase) -> int:
    integer = int(pipe_read_line(prefix, input))

    return integer


def pipe_read_string_maybe(prefix, input: TextIOBase) -> str | None:
    length = pipe_read_int(prefix, input)

    if length < 0:
        return None

    string = input.read(length)

    return string


def pipe_read_string(prefix, input: TextIOBase) -> str:
    length = pipe_read_int(prefix, input)

    string = input.read(length)

    return string


def pipe_read_strings(prefix, input: TextIOBase) -> Iterable[str]:
    while True:
        string = pipe_read_string_maybe(prefix, input)

        if string is None:
            break

        yield string


def pipe_write_line(prefix, output: TextIOBase, line: str) -> None:
    output.write(f"{line}\n")


def pipe_write_int(prefix, output: TextIOBase, integer: int) -> None:
    pipe_write_line(prefix, output, str(integer))


def pipe_write_string(prefix, output: TextIOBase, string: str) -> None:
    string_length = len(string)

    pipe_write_int(prefix, output, string_length)

    output.write(string)
