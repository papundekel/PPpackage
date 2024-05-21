from contextlib import contextmanager
from os import mkfifo
from pathlib import Path
from shutil import move
from tempfile import TemporaryDirectory as BaseTemporaryDirectory


@contextmanager
def TemporaryDirectory(dir=None):
    with BaseTemporaryDirectory(dir=dir) as dir_path_string:
        dir_path = Path(dir_path_string)

        yield dir_path


@contextmanager
def TemporaryPipe(dir=None):
    with TemporaryDirectory(dir) as dir_path:
        pipe_path = dir_path / "pipe"

        mkfifo(pipe_path)

        yield pipe_path


def rmtree(path: Path):
    if not path.exists():
        pass
    elif not path.is_symlink() and path.is_dir():
        temp = BaseTemporaryDirectory()
        temp.cleanup()
        temp.name = str(path)
        temp.cleanup()
    else:
        path.unlink()


def wipe_directory(directory: Path) -> None:
    for path in directory.iterdir():
        rmtree(path)


def movetree(source: Path, destination: Path):
    for source_item in source.iterdir():
        destination_item = destination / source_item.name
        rmtree(destination_item)

        if not source_item.is_symlink() and source_item.is_dir():
            destination_item.mkdir()
            movetree(source_item, destination_item)
            source_item.rmdir()
        else:
            move(source_item, destination_item)
