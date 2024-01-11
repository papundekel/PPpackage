from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from secrets import token_hex
from typing import Annotated, Any, AsyncContextManager, Generic, TypeVar

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse as BaseStreamingResponse
from pydantic import AnyUrl
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import joinedload
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException
from starlette.responses import ContentStream
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


@asynccontextmanager
async def get_session_from_engine(engine: AsyncEngine):
    async with AsyncSession(engine) as session:
        yield session


class TokenBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    token: str = Field(unique=True)
    admin: bool


class UserBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="tokendb.id", unique=True)


SettingsType = TypeVar("SettingsType", bound=BaseSettings)
StateType = TypeVar("StateType")
TokenDBType = TypeVar("TokenDBType", bound=TokenBase)
UserDBType = TypeVar("UserDBType", bound=UserBase)


def HTTP401Exception():
    return HTTPException(status_code=HTTP_401_UNAUTHORIZED)


def HTTP403Exception():
    return HTTPException(status_code=HTTP_403_FORBIDDEN)


def HTTP404Exception():
    return HTTPException(status_code=HTTP_404_NOT_FOUND)


def HTTP400Exception():
    return HTTPException(status_code=HTTP_400_BAD_REQUEST)


async def create_token(session: AsyncSession, TokenDB: type[TokenDBType], **kwargs):
    token = token_hex(32)

    token_db = TokenDB(token=token, **kwargs)

    session.add(token_db)

    await session.commit()
    await session.refresh(token_db)

    return token_db


Model = TypeVar("Model", bound=SQLModel)


async def get_not_primary(
    session: AsyncSession, ModelDB: type[Model], column: Any, pk: Any, *options: Any
) -> Model | None:
    query = select(ModelDB).where(column == pk)

    if options != ():
        query = query.options(*options)

    instance_db = (await session.exec(query)).first()
    return instance_db


def StreamingResponse(
    status_code: int,
    generator: Callable[[], ContentStream],
):
    return BaseStreamingResponse(
        generator(), status_code=status_code, media_type="application/octet-stream"
    )


class Framework(Generic[TokenDBType, UserDBType]):
    def __init__(
        self,
        TokenDB: type[TokenDBType],
        UserDB: type[UserDBType],
    ):
        def get_state(request: Request):
            return request.app.state.state

        async def get_session(request: Request):
            async with get_session_from_engine(request.app.state.engine) as session:
                yield session

        async def get_token(
            request: Request,
            session: Annotated[AsyncSession, Depends(get_session)],
        ) -> TokenDBType:
            header = request.headers.get("Authorization")

            if header is None:
                raise HTTP401Exception()

            scheme, token = header.split()

            if scheme.lower() != "bearer":
                raise HTTP401Exception()

            token_db = await get_not_primary(
                session, TokenDB, TokenDB.token, token, joinedload(TokenDB.user)
            )

            if token_db is None:
                raise HTTP401Exception()

            return token_db

        async def get_user(token: Annotated[TokenDBType, Depends(get_token)]) -> UserDB:
            user_db = token.user

            if user_db is None:
                raise HTTP401Exception()

            return user_db

        async def create_admin_token(engine: AsyncEngine) -> str:
            async with get_session_from_engine(engine) as session:
                token_db = await create_token(session, TokenDB, admin=True)

                return token_db.token

        async def create_user(
            session: Annotated[AsyncSession, Depends(get_session)],
            token: Annotated[TokenDBType, Depends(get_token)],
        ) -> TokenDBType:
            if not token.admin:
                raise HTTP403Exception()

            user_token_db = await create_token(session, TokenDB, admin=False)

            return user_token_db

        self.get_state = get_state
        self.get_session = get_session
        self.get_token = get_token
        self.get_user = get_user
        self.create_admin_token = create_admin_token
        self.create_user = create_user


class Server(FastAPI, Generic[SettingsType, StateType, TokenDBType, UserDBType]):
    def __init__(
        self,
        settings: SettingsType,
        framework: Framework[TokenDBType, UserDBType],
        database_url: AnyUrl,
        lifespan: Callable[[SettingsType], AsyncContextManager[StateType]],
        UserDB: type[UserDBType],
        create_user_kwargs: Callable[[], Mapping[str, Any]],
    ):
        @asynccontextmanager
        async def lifespan_wrap(app: FastAPI):
            engine = create_async_engine(
                str(database_url),
                echo=False,
                connect_args={"check_same_thread": False},
            )

            async with lifespan(settings) as state:
                app.state.state = state
                app.state.engine = engine
                yield
                app.state.engine = None
                app.state.state = None

            await engine.dispose()

        async def user(
            session: Annotated[AsyncSession, Depends(framework.get_session)],
            token_db: Annotated[TokenDBType, Depends(framework.create_user)],
        ) -> str:
            session.add(UserDB(token_id=token_db.id, **create_user_kwargs()))

            await session.commit()
            await session.refresh(token_db)

            return token_db.token

        super().__init__(
            debug=getattr(settings, "debug", False),
            lifespan=lifespan_wrap,
            redoc_url=None,
        )
        super().post("/user")(user)
