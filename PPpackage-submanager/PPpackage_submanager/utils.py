from dataclasses import dataclass
from pathlib import Path

from PPpackage_submanager.exceptions import CommandException


def _command_exception(f):
    def decorator(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            raise CommandException

    return decorator


class Installations:
    def __init__(self, max: int):
        self.mapping = dict[int, memoryview]()
        self.max = max
        self.i = 0

    @_command_exception
    def _find_new_i(self, i: int) -> int:
        new_i = i + 1

        while new_i in self.mapping:
            if new_i >= self.max:
                new_i = 0

            new_i += 1

        return new_i

    @_command_exception
    def add(self, installation: memoryview) -> str:
        i = self.i

        self.mapping[i] = installation

        self.i = self._find_new_i(i)

        return str(i)

    @_command_exception
    def put(self, id: str, installation: memoryview) -> None:
        i = int(id)

        self.mapping[i] = installation

    @_command_exception
    def get(self, id: str) -> memoryview:
        i = int(id)

        return self.mapping[i]

    @_command_exception
    def remove(self, id: str) -> None:
        i = int(id)

        del self.mapping[i]


@dataclass(frozen=True)
class RunnerInfo:
    socket_path: Path
    workdirs_path: Path
