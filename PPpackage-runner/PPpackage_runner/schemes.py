from pathlib import Path

from pydantic import BaseModel


class UserResponse(BaseModel):
    token: str
    workdir_relative_path: Path
