from functools import partial

from PPpackage_utils.app import fetch_receive_discard, generate_empty, init, run
from PPpackage_utils.utils import anoop

from .fetch import fetch_send
from .install import install
from .resolve import resolve


def main():
    app = init(
        anoop,
        resolve,
        partial(fetch_receive_discard, fetch_send),
        generate_empty,
        install,
        str,
    )
    run(app, "PP")
