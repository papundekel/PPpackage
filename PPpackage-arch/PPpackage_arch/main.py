from functools import partial

from PPpackage_utils.submanager import (
    fetch_receive_discard,
    generate_empty,
    submanager_main,
)

from .fetch import fetch_send
from .install import install
from .resolve import resolve
from .update_database import update_database

PROGRAM_NAME = "PPpackage-arch"

main = partial(
    submanager_main,
    update_database,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate_empty,
    install,
    str,
    PROGRAM_NAME,
)
