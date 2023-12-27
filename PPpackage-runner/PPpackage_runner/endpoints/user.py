from tempfile import mkdtemp
from typing import Annotated

from anyio import Path
from fastapi import Depends
from PPpackage_runner.database import TokenDB, UserDB
from PPpackage_runner.settings import WORKDIRS_PATH
from PPpackage_runner.utils import framework
from sqlmodel.ext.asyncio.session import AsyncSession


async def user(
    session: Annotated[AsyncSession, Depends(framework.get_session)],
    token_db: Annotated[TokenDB, Depends(framework.create_user)],
) -> str:
    workdir_path = Path(mkdtemp(dir=WORKDIRS_PATH))

    workdir_relative_path = workdir_path.relative_to(WORKDIRS_PATH)

    session.add(
        UserDB(token_id=token_db.id, workdir_relative_path=str(workdir_relative_path))
    )

    await session.commit()
    await session.refresh(token_db)

    return token_db.token
