from asyncio import TaskGroup
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from secrets import token_hex
from typing import Annotated, Any, Generic, TypeVar
from typing import cast as type_cast

from fastapi import Depends, Request
from fastapi.responses import StreamingResponse as BaseStreamingResponse
from PPpackage_utils.http_stream import HTTPReader, HTTPWriter
from PPpackage_utils.stream import Reader, Writer
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import joinedload
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.datastructures import ImmutableMultiDict
from starlette.exceptions import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)


@asynccontextmanager
async def get_session_from_engine(engine: AsyncEngine):
    async with AsyncSession(engine) as session:
        yield session


@dataclass(frozen=True)
class State:
    engine: AsyncEngine


class TokenBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    token: str = Field(unique=True)
    admin: bool


class UserBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="tokendb.id", unique=True)


StateType = TypeVar("StateType", bound=State)
TokenDBType = TypeVar("TokenDBType", bound=TokenBase)
UserType = TypeVar("UserType", bound=UserBase)
UserDBType = TypeVar("UserDBType", bound=UserBase)


def HTTP401Exception():
    return HTTPException(status_code=HTTP_401_UNAUTHORIZED)


def HTTP403Exception():
    return HTTPException(status_code=HTTP_403_FORBIDDEN)


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


class Framework(Generic[StateType, TokenDBType, UserType, UserDBType]):
    def __init__(
        self,
        State: type[StateType],
        TokenDB: type[TokenDBType],
        User: type[UserType],
        UserDB: type[UserDBType],
    ):
        def get_state(request: Request) -> StateType:
            return type_cast(StateType, request.app.state.state)

        async def get_session(state: Annotated[StateType, Depends(get_state)]):
            async with get_session_from_engine(state.engine) as session:
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

        async def get_user(
            token: Annotated[TokenDBType, Depends(get_token)]
        ) -> UserType:
            user_db = token.user

            if user_db is None:
                raise HTTP401Exception()

            return User.model_validate(user_db)

        def create_endpoint(
            handler: Callable[
                [StateType, ImmutableMultiDict[str, Any], UserType, Reader, Writer],
                Coroutine[Any, Any, None],
            ]
        ):
            async def endpoint(
                request: Request, user: Annotated[UserType, Depends(get_user)]
            ):
                if not isinstance(request.user, User):
                    raise HTTPException(403)

                async def generator():
                    writer = HTTPWriter()

                    async with TaskGroup() as group:
                        group.create_task(
                            handler(
                                get_state(request),
                                request.query_params,
                                user,
                                HTTPReader(request),
                                writer,
                            )
                        )

                        async for chunk in writer.iterate():
                            yield chunk

                return BaseStreamingResponse(
                    generator(), media_type="application/octet-stream"
                )

            return endpoint

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
        self.create_endpoint = create_endpoint
        self.create_admin_token = create_admin_token
        self.create_user = create_user
