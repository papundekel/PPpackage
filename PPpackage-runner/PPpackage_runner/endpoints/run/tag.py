from PPpackage_runner.database import User
from PPpackage_runner.utils import State
from PPpackage_utils.stream import Reader, Writer
from starlette.datastructures import ImmutableMultiDict

from . import run


async def run_tag(
    state: State,
    query_parameters: ImmutableMultiDict[str, str],
    user: User,
    reader: Reader,
    writer: Writer,
):
    tag = query_parameters["tag"]

    return await run(user, tag, query_parameters)
