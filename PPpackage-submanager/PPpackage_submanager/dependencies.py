from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from .database import Token, User
from .utils import HTTP401Exception, HTTP403Exception, get_not_primary, get_session


async def get_token_from_header(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Token:
    header = request.headers.get("Authorization")

    if header is None:
        raise HTTP401Exception()

    scheme, token = header.split()

    if scheme.lower() != "bearer":
        raise HTTP401Exception()

    token_db = await get_not_primary(
        session,
        Token,
        Token.token,
        token,
        joinedload(Token.user),  # type: ignore
    )

    if token_db is None:
        raise HTTP401Exception()

    return token_db


async def require_admin_token(
    token: Annotated[Token, Depends(get_token_from_header)],
):
    if not token.admin:
        raise HTTP403Exception()


async def get_user(token: Annotated[Token, Depends(get_token_from_header)]) -> User:
    user_db = token.user

    if user_db is None:
        raise HTTP401Exception()

    return user_db
