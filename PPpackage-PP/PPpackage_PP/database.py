from typing import Optional

from PPpackage_utils.server import TokenBase, UserBase
from sqlmodel import Relationship


class TokenDB(TokenBase, table=True):
    user: Optional["UserDB"] = Relationship(back_populates="token")


class UserDB(UserBase, table=True):
    token: TokenDB = Relationship(back_populates="user")


class User(UserBase):
    token: TokenDB
