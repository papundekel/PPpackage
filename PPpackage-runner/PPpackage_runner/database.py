from pathlib import Path
from typing import Optional

from PPpackage_runner.settings import settings
from PPpackage_utils.server import TokenBase, UserBase
from sqlmodel import Relationship


class Token(TokenBase, table=True):
    user: Optional["User"] = Relationship(back_populates="token")


class User(UserBase, table=True):
    workdir_relative_path: str
    token: Token = Relationship(back_populates="user")

    @property
    def workdir_path(self) -> Path:
        return settings.workdirs_path / Path(self.workdir_relative_path)
