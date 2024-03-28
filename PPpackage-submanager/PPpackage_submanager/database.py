from pathlib import Path
from secrets import token_hex
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field, Relationship, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .utils import HTTP404Exception, get_session_from_engine


class Token(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    token: str = Field(unique=True)
    admin: bool

    user: Optional["User"] = Relationship(back_populates="token")


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="token.id", unique=True)

    token: Token = Relationship(back_populates="user")
    installations: list["Installation"] = Relationship(back_populates="user")


class Installation(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    path_raw: str = Field(unique=True)
    user_id: int = Field(foreign_key="user.id")

    user: User = Relationship(back_populates="installations")

    def __init__(self, path: Path):
        super().__init__(path_raw=str(path))  # type: ignore

    @property
    def path(self):
        return Path(self.path_raw)


async def get_installation(session: AsyncSession, installation_id: str, user_id: int):
    statement = select(Installation).where(
        Installation.id == int(installation_id) and Installation.user_id == user_id
    )
    installation = (await session.exec(statement)).first()

    if installation is None:
        raise HTTP404Exception()

    return installation


async def create_token(session: AsyncSession, admin: bool):
    token = token_hex(32)

    token_db = Token(token=token, admin=admin)

    session.add(token_db)

    await session.commit()
    await session.refresh(token_db)

    return token_db


async def create_admin_token(engine: AsyncEngine) -> str:
    async with get_session_from_engine(engine) as session:
        token_db = await create_token(session, admin=True)

    return token_db.token
