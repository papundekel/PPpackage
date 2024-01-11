from collections.abc import Mapping
from pathlib import Path
from tempfile import mkdtemp

from PPpackage_runner.database import User
from PPpackage_runner.schemes import UserResponse
from PPpackage_runner.settings import settings


def create_user_kwargs() -> Mapping[str, str]:
    workdir_path = Path(mkdtemp(dir=settings.workdirs_path))

    workdir_relative_path = workdir_path.relative_to(settings.workdirs_path)

    return {"workdir_relative_path": str(workdir_relative_path)}


def create_user_response(token: str, user: User):
    return UserResponse(
        token=token, workdir_relative_path=Path(user.workdir_relative_path)
    )
