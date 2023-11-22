from PPpackage_utils.app import init, run
from PPpackage_utils.utils import anoop

from .fetch import receive as fetch_receive
from .fetch import send as fetch_send
from .install import install
from .resolve import resolve
from .update_database import update_database


def main():
    app = init(
        update_database,
        resolve,
        fetch_send,
        fetch_receive,
        anoop,
        install,
        str,
    )
    run(app, "arch")
