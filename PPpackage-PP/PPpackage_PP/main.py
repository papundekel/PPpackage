from PPpackage_utils.app import generate_empty, init, run
from PPpackage_utils.utils import anoop

from .fetch import receive as fetch_receive
from .fetch import send as fetch_send
from .install import install
from .resolve import resolve


def main():
    app = init(
        anoop,
        resolve,
        fetch_send,
        fetch_receive,
        generate_empty,
        install,
        str,
    )
    run(app, "PP")
