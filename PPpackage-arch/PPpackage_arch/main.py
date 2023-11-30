from functools import partial

from PPpackage_utils.app import fetch_receive_discard, generate_empty, init, run

from .fetch import fetch_send
from .install import install
from .resolve import resolve
from .update_database import update_database


def main():
    app = init(
        update_database,
        resolve,
        partial(fetch_receive_discard, fetch_send),
        generate_empty,
        install,
        str,
    )
    run(app, "arch")
