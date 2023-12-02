from functools import partial

from PPpackage_utils.submanager import fetch_receive_discard, generate_empty, main

from .fetch import fetch_send
from .install import install
from .resolve import resolve
from .update_database import update_database

main(
    "arch",
    update_database,
    resolve,
    partial(fetch_receive_discard, fetch_send),
    generate_empty,
    install,
    str,
)
