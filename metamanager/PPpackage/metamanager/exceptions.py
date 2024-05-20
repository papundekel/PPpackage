from collections.abc import Iterable
from typing import IO

from PPpackage.repository_driver.interface.schemes import Requirement


class PrintableException(Exception):
    def print(self, output: IO[str]) -> None:
        print(self, file=output)


def print_exception_group[
    T: PrintableException
](output: IO[str], exception_group: BaseExceptionGroup[T]) -> None:
    for subexception in exception_group.exceptions:
        match subexception:
            case PrintableException():
                subexception.print(output)
            case subexception_group:
                print_exception_group(output, subexception_group)


class SubmanagerCommandFailure(Exception):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class EpochException(Exception):
    pass


class NoModelException(PrintableException):
    def __init__(self, requirements: Iterable[Requirement] | None = None):
        super().__init__()

        self.requirements = (
            requirements if requirements is not None else list[Requirement]()
        )

    def print(self, output: IO[str]) -> None:
        output.write("No model found for the following requirements:")

        for requirement in self.requirements:
            output.write(f"\t{requirement}\n")


class BuildException(Exception):
    pass
