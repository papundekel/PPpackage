from collections.abc import Iterable
from typing import IO

from PPpackage.repository_driver.interface.schemes import Requirement


class HandledException(Exception):
    def handle(self, output: IO[str]) -> None: ...


def handle_exception_group[
    T: HandledException
](output: IO[str], exception_group: BaseExceptionGroup[T]) -> None:
    for subexception in exception_group.exceptions:
        match subexception:
            case HandledException():
                subexception.handle(output)
            case subexception_group:
                handle_exception_group(output, subexception_group)


class SubmanagerCommandFailure(Exception):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class EpochException(Exception):
    pass


class NoModelException(HandledException):
    def __init__(self, requirements: Iterable[Requirement] | None = None):
        super().__init__()

        self.requirements = (
            requirements if requirements is not None else list[Requirement]()
        )

    def handle(self, output: IO[str]) -> None:
        output.write("No model found for the following requirements:\n")

        for requirement in self.requirements:
            output.write(f"\t{requirement}\n")

        exit(2)
