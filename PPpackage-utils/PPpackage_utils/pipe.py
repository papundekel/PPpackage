from collections.abc import Iterable
from io import TextIOBase
from sys import stderr

from PPpackage_utils.utils import MyException

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
        stderr.write(f"DEBUG {prefix}: pipe read line: {line}\n")

    return line


def pipe_read_int(debug, prefix, input: TextIOBase) -> int:
    integer = int(pipe_read_line(debug, prefix, input))

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe read int: {integer}\n")

    return integer


def pipe_read_string_maybe(debug, prefix, input: TextIOBase) -> str | None:
    length = pipe_read_int(debug, prefix, input)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe read string maybe length: {length}\n")

    if length < 0:
        return None

    string = input.read(length)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe read string maybe string: {string}\n")

    return string


def pipe_read_string(debug, prefix, input: TextIOBase) -> str:
    length = pipe_read_int(debug, prefix, input)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe read string length: {length}\n")

    string = input.read(length)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe read string string: {string}\n")

    return string


def pipe_read_strings(debug, prefix, input: TextIOBase) -> Iterable[str]:
    while True:
        string = pipe_read_string_maybe(debug, prefix, input)

        if _DEBUG:
            stderr.write(f"DEBUG {prefix}: pipe read strings string: {string}\n")

        if string is None:
            break

        yield string


def pipe_write_line(debug, prefix, output: TextIOBase, line: str) -> None:
    output.write(f"{line}\n")

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe write line: {line}\n")


def pipe_write_int(debug, prefix, output: TextIOBase, integer: int) -> None:
    pipe_write_line(debug, prefix, output, str(integer))

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe write int: {integer}\n")


def pipe_write_string(debug, prefix, output: TextIOBase, string: str) -> None:
    string_length = len(string)

    pipe_write_int(debug, prefix, output, string_length)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe write string length: {string_length}\n")

    output.write(string)

    if _DEBUG:
        stderr.write(f"DEBUG {prefix}: pipe write string string: {string}\n")
