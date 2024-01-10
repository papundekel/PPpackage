from collections.abc import Mapping
from tempfile import mkdtemp

from anyio import Path
from PPpackage_runner.settings import settings


def create_user_kwargs() -> Mapping[str, str]:
    workdir_path = Path(mkdtemp(dir=settings.workdirs_path))

    workdir_relative_path = workdir_path.relative_to(settings.workdirs_path)

    return {"workdir_relative_path": str(workdir_relative_path)}
