from pathlib import Path
from typing import Optional

from PPpackage_utils.server import HTTP404Exception, TokenBase, UserBase
from sqlmodel import Field, Relationship, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


class Token(TokenBase, table=True):
    user: Optional["User"] = Relationship(back_populates="token")


class User(UserBase, table=True):
    token: Token = Relationship(back_populates="user")
    installations: list["Installation"] = Relationship(back_populates="user")


class Installation(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    path_raw: str = Field(unique=True)
    user_id: int = Field(foreign_key="user.id")

    user: User = Relationship(back_populates="installations")

    def __init__(self, path: Path):
        super().__init__(path_raw=str(path))

    @property
    def path(self):
        return Path(self.path_raw)


async def get_installation(session: AsyncSession, installation_id: int, user_id: int):
    statement = select(Installation).where(
        Installation.id == installation_id and Installation.user_id == user_id
    )
    installation = (await session.exec(statement)).first()

    if installation is None:
        raise HTTP404Exception()

    return installation
