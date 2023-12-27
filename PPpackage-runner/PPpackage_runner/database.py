from pathlib import Path
from typing import Optional

from PPpackage_runner.settings import WORKDIRS_PATH
from PPpackage_utils.server import TokenBase, UserBase
from sqlmodel import Relationship


class TokenDB(TokenBase, table=True):
    user: Optional["UserDB"] = Relationship(back_populates="token")


class UserDB(UserBase, table=True):
    workdir_relative_path: str
    token: TokenDB = Relationship(back_populates="user")


class User(UserBase):
    workdir_relative_path: Path
    token: TokenDB

    @property
    def workdir_path(self) -> Path:
        return WORKDIRS_PATH / self.workdir_relative_path
