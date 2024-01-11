from collections.abc import Mapping

from pydantic import BaseModel

from .database import User


def create_user_kwargs() -> Mapping[str, str]:
    return {}


class UserResponse(BaseModel):
    dummy: None = None


def create_user_response(token: str, user: User):
    return UserResponse()
